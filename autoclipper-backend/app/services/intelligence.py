from groq import Groq
import logging
import json
from app.core.settings import settings

logger = logging.getLogger(__name__)

class Intelligence:
    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = "llama-3.3-70b-versatile"

    def analyze_transcript(self, transcript_segments: list[dict]) -> list[dict]:
        """
        Analyze transcript and return viral clip candidates using Groq.
        """
        full_text = ""
        for seg in transcript_segments:
            start = int(seg['start'])
            text = seg['text']
            full_text += f"[{start}s] {text}\n"

        prompt = """
        You are an expert video editor. Your task is to extract ONLY the absolute best 1 to 3 segments for a viral TikTok/Short.
        
        CRITICAL RULES:
        1.  **Context is King**: Do NOT start or end a clip in the middle of a sentence.
        2.  **Less is More**: Only return segments that are truly engaging. If the whole video is boring, return an empty list.
        3.  **Duration**: Each clip MUST be between 60 and 120 seconds. IF a segment is too short, MERGE it with previous/next sentences to reach 60s. Do NOT return clips shorter than 55 seconds.
        4.  **Quantity**: Maximum 3 clips. Prefer 1 or 2 high-quality long clips over short ones.
        
        Output Format:
        Return STRICT JSON format (a list of objects).
        Keys:
        - start_timestamp (float)
        - end_timestamp (float)
        - virality_score (int 1-100)
        - reasoning (string)
        - suggested_caption (string)

        Transcript:
        """ + full_text[:100000]

        logger.info("Sending transcript to Groq (Llama 3) for analysis...")
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that outputs JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                stream=False,
                response_format={"type": "json_object"}
            )
            
            response_text = completion.choices[0].message.content
            logger.info(f"Groq response: {response_text[:100]}...")
            
            result = json.loads(response_text)
            
            # Normalize potential wrapper keys
            if isinstance(result, list):
                return result
            # Groq/Llama usually wraps in a key if asked for JSON object
            for key in ["clips", "segments", "candidates"]:
                if key in result:
                    return result[key]
            
            # If it returns a dict but unknown key, try to find a list value
            for val in result.values():
                if isinstance(val, list):
                    return val
            
            return []
            
        except Exception as e:
            logger.error(f"Intelligence analysis failed: {e}")
            raise
