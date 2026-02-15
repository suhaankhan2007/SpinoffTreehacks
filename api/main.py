"""
Text-to-Sign Language REST API

A lightweight FastAPI service that translates spoken language text into sign language
output in multiple formats (pose binary, video, or JSON metadata).

Wraps the sign.mt cloud functions at us-central1-sign-mt.cloudfunctions.net.
"""

from enum import Enum
from urllib.parse import urlencode

import httpx
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

# ---------------------------------------------------------------------------
# Cloud function base URLs (hosted by sign.mt)
# ---------------------------------------------------------------------------
POSE_API = "https://us-central1-sign-mt.cloudfunctions.net/spoken_text_to_signed_pose"
VIDEO_API = "https://us-central1-sign-mt.cloudfunctions.net/spoken_text_to_signed_video"

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Text-to-Sign Language API",
    description=(
        "Translate spoken language text into sign language. "
        "Returns pose data, video, or JSON metadata depending on the requested format."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
class OutputFormat(str, Enum):
    json = "json"
    pose = "pose"
    video = "video"


def _build_query(text: str, spoken: str, signed: str) -> str:
    """Build the query string shared by both cloud function URLs."""
    return urlencode({"text": text, "spoken": spoken, "signed": signed})


async def _proxy_stream(url: str, media_type: str) -> StreamingResponse:
    """
    Fetch the full response from *url* and return it as a FastAPI
    ``StreamingResponse``.  We download the entire payload first so that the
    httpx client can be cleanly closed before the response begins streaming
    back to the caller (avoids context-manager lifetime issues).
    """
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        upstream = await client.get(url)

        if upstream.status_code != 200:
            raise HTTPException(
                status_code=upstream.status_code,
                detail=f"Upstream error: {upstream.text}",
            )

        content = upstream.content  # full bytes

    async def _iter():
        # Yield in chunks so FastAPI streams the response
        offset = 0
        while offset < len(content):
            yield content[offset : offset + 8192]
            offset += 8192

    return StreamingResponse(_iter(), media_type=media_type)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/")
async def root():
    """Health-check / welcome message."""
    return {
        "service": "Text-to-Sign Language API",
        "docs": "/docs",
        "usage": "GET /translate?text=Hello&format=json",
    }


@app.get("/translate")
async def translate(
    text: str = Query(..., description="The spoken language text to translate"),
    spoken: str = Query("en", description="Spoken language code (e.g. en, de, fr)"),
    signed: str = Query("ase", description="Signed language code (e.g. ase for ASL, gsg for German Sign Language)"),
    format: OutputFormat = Query(OutputFormat.json, description="Output format: json, pose, or video"),
):
    """
    Translate spoken language text into sign language.

    - **json** returns metadata and direct URLs you can embed in your app.
    - **pose** streams the raw `.pose` binary file (application/octet-stream).
    - **video** streams an MP4 video of the signed translation (video/mp4).
    """
    if not text.strip():
        raise HTTPException(status_code=400, detail="'text' must not be empty")

    qs = _build_query(text, spoken, signed)
    pose_url = f"{POSE_API}?{qs}"
    video_url = f"{VIDEO_API}?{qs}"

    # --- JSON: return metadata + URLs the caller can fetch themselves ----------
    if format == OutputFormat.json:
        return JSONResponse(
            content={
                "text": text,
                "spoken": spoken,
                "signed": signed,
                "pose_url": pose_url,
                "video_url": video_url,
            }
        )

    # --- POSE: stream the .pose binary from the cloud function ----------------
    if format == OutputFormat.pose:
        return await _proxy_stream(pose_url, media_type="application/octet-stream")

    # --- VIDEO: stream the MP4 from the cloud function ------------------------
    if format == OutputFormat.video:
        return await _proxy_stream(video_url, media_type="video/mp4")


# ---------------------------------------------------------------------------
# Run with: uvicorn main:app --reload --port 8000
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

