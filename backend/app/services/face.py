class FaceService:
    async def detect_and_segment(self, photo_base64: str) -> dict:
        """Stub: In production, call Aliyun SegmentHair API.
        Returns face detection result."""
        return {"face_detected": True, "segment_ok": True}


face_service = FaceService()
