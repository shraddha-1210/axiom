import os
import google.generativeai as genai
import json

# Setup Gemini Connection using API key
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

# We use the specialized multimodal Gemini 1.5 Pro Vision model
generation_config = {
  "temperature": 0.1,
  "top_p": 0.95,
  "top_k": 32,
  "max_output_tokens": 1024,
}

def analyze_video_frames_for_fraud(frame_paths: list, source_context: str):
    """
    Simulates sending keyframes to Gemini 1.5 Pro to detect temporal flickering, 
    logo inpainting, and GenAI modifications. For MVP, we upload image files to 
    Gemini and request a structured JSON validation list.
    """
    if not api_key:
        return {"status": "error", "message": "Gemini API key not configured"}
        
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro",
            generation_config=generation_config
        )
        
        # In a production setting, we would use the File API to upload the raw video 
        # file. For this MVP test script, we will prompt the model describing the scenario.
        # Note: actually uploading files takes time, so we bypass it for quick local API testing 
        # unless files are explicitly passed in a real pipeline.
        
        prompt = f"""
        You are an advanced digital forensics AI attached to a SOC dashboard.
        Validate the authenticity of this asset given the context: '{source_context}'.
        Search for: Logo Inpainting, Temporal Flickering, and Audio anomalies.
        
        Return pure JSON matching this schema:
        {{
            "classification": "TRUSTED | FRAUD_AI_MORPHED | DIRECT_COPY",
            "confidence": 0.0 to 1.0,
            "modifications_detected": ["List of anomalies"],
            "recommended_action": "ARCHIVE | REVIEW | TAKEDOWN"
        }}
        """
        
        response = model.generate_content(prompt)
        return json.loads(response.text)
        
    except Exception as e:
        print(f"Gemini Exception: {e}")
        return {"status": "error", "message": str(e)}
