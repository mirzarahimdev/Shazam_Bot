from typing import Optional

VIDEO_CATEGORIES = {
    "video": "🎬 Video",
    "lesson": "📚 Dars",
    "fun": "😂 Ko‘ngilochar",
    "useful": "💡 Foydali",
    "music": "🎵 Musiqa",
    "favorite": "⭐️ Sevimli",
    "other": "📁 Boshqa",
}

ALLOWED_VIDEO_MIME = {
    "video/mp4",
    "video/mpeg",
    "video/quicktime",
    "video/x-msvideo",
    "video/webm",
}


class VideoService:
    @staticmethod
    def category_label(key: str) -> str:
        return VIDEO_CATEGORIES.get(key, VIDEO_CATEGORIES["other"])

    @staticmethod
    def validate_size(file_size: Optional[int], max_bytes: int) -> bool:
        if file_size is None:
            return True
        return file_size <= max_bytes

    @staticmethod
    def validate_mime(mime_type: Optional[str]) -> bool:
        if not mime_type:
            return True
        return mime_type.lower() in ALLOWED_VIDEO_MIME
