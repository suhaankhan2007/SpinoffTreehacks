# Text-to-Sign Language REST API

A lightweight FastAPI microservice that translates spoken language text into sign language output.

## Quick Start

```bash
# 1. Create a virtual environment (recommended)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the server
uvicorn main:app --reload --port 8000
```

The API is now running at **http://localhost:8000**.
Interactive Swagger docs are at **http://localhost:8000/docs**.

## Endpoint

### `GET /translate`

| Parameter | Required | Default | Description                                              |
| --------- | -------- | ------- | -------------------------------------------------------- |
| `text`    | yes      | —       | Spoken language text to translate                        |
| `spoken`  | no       | `en`    | Spoken language code (`en`, `de`, `fr`, …)               |
| `signed`  | no       | `ase`   | Signed language code (`ase` = ASL, `gsg` = German SL, …) |
| `format`  | no       | `json`  | Output format: `json`, `pose`, or `video`                |

### Response formats

**`json`** — metadata + direct cloud URLs:

```bash
curl "http://localhost:8000/translate?text=Hello&format=json"
```

```json
{
  "text": "Hello",
  "spoken": "en",
  "signed": "ase",
  "pose_url": "https://...signed_pose?text=Hello&spoken=en&signed=ase",
  "video_url": "https://...signed_video?text=Hello&spoken=en&signed=ase"
}
```

**`pose`** — raw `.pose` binary (application/octet-stream):

```bash
curl -o hello.pose "http://localhost:8000/translate?text=Hello&format=pose"
```

**`video`** — MP4 video stream (video/mp4):

```bash
curl -o hello.mp4 "http://localhost:8000/translate?text=Hello&format=video"
```

## Integration Examples

### Python (requests)

```python
import requests

# Get JSON metadata
resp = requests.get("http://localhost:8000/translate", params={
    "text": "How are you?",
    "spoken": "en",
    "signed": "ase",
    "format": "json",
})
data = resp.json()
print(data["video_url"])  # Use this URL in a <video> tag

# Download video directly
resp = requests.get("http://localhost:8000/translate", params={
    "text": "How are you?",
    "format": "video",
}, stream=True)
with open("output.mp4", "wb") as f:
    for chunk in resp.iter_content(chunk_size=8192):
        f.write(chunk)
```

### JavaScript (fetch)

```javascript
// Get JSON metadata
const resp = await fetch('http://localhost:8000/translate?text=Hello&format=json');
const data = await resp.json();

// Use the video URL in an HTML video element
const video = document.createElement('video');
video.src = data.video_url;
video.autoplay = true;
document.body.appendChild(video);
```

### HTML embed

```html
<!-- Directly embed the video stream -->
<video autoplay loop>
  <source src="http://localhost:8000/translate?text=Hello&format=video" type="video/mp4" />
</video>
```

## Supported Languages

**Spoken languages:** en, de, fr, es, it, ja, ko, zh, ar, hi, pt, ru, and 100+ more.

**Signed languages:** ase (ASL), gsg (German SL), fsl (French SL), bfi (British SL), and 50+ more.

See the full list in the [sign.mt app](https://sign.mt/).
