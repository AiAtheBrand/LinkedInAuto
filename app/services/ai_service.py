import logging
import os
import re
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

logger = logging.getLogger(__name__)


class AIService:

    def __init__(self, client: Groq | None = None):
        api_key = os.getenv("GROQ_API_KEY")
        self.client = client or Groq(api_key=api_key)
        self.primary_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.fallback_model = "llama-3.1-8b-instant"

    def generate_linkedin_post(
        self,
        topic: str,
        category: str,
        problem: str | None,
        what_i_learned: str,
        project: str | None,
        lesson: str | None
    ) -> str:
        prompt = f"""
You are helping a software engineer document their learning journey on LinkedIn.

Create an authentic, complete LinkedIn post using ONLY the information provided below.

Topic:
{topic}

Category:
{category}

Problem:
{problem or "None specified"}

What I learned:
{what_i_learned}

Project:
{project or "Personal project / Engineering practice"}

Lesson:
{lesson or "None specified"}

Requirements:
- Write in first person ("I", "my").
- Sound authentic, thoughtful, and conversational.
- Keep the tone professional.
- Explain the technical concept clearly.
- Do not invent experiences or exaggerated achievements.
- Avoid generic motivational cliché language.
- Avoid excessive emojis (use 2-3 at most).
- Start with an engaging, natural hook.
- Share the technical takeaway or problem-solving breakdown clearly.
- End with a useful conclusion, thoughtful question, or actionable takeaway.
- IMPORTANT: Complete the post fully from start to finish. Never stop mid-sentence or leave thoughts incomplete.
"""

        system_instruction = (
            "You are an expert LinkedIn copywriter for software engineers. "
            "Write engaging, authentic, and complete posts. "
            "Ensure the post is fully written and finished without being cut off."
        )

        models_to_try = [self.primary_model]
        if self.fallback_model != self.primary_model:
            models_to_try.append(self.fallback_model)

        last_error = None
        for model_name in models_to_try:
            try:
                response = self.client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2048,  # Ample space to prevent cutting off in the middle
                    temperature=0.7
                )
                raw_content = response.choices[0].message.content or ""
                cleaned = self._clean_ai_output(raw_content)
                if cleaned:
                    return cleaned
            except Exception as exc:
                logger.warning(f"AI generation failed with model {model_name}: {str(exc)}")
                last_error = exc

        raise RuntimeError(f"All AI models failed to generate content: {str(last_error)}")

    def _clean_ai_output(self, text: str) -> str:
        """Strips markdown code fences and extraneous wrapper quotes."""
        trimmed = text.strip()
        # Remove ```markdown ... ``` or ``` ... ``` if the LLM wrapped it
        if trimmed.startswith("```"):
            trimmed = re.sub(r"^```[a-zA-Z]*\n?", "", trimmed)
            trimmed = re.sub(r"\n?```$", "", trimmed)
            trimmed = trimmed.strip()

        # Remove surrounding double quotes if the LLM quoted the entire response
        if trimmed.startswith('"') and trimmed.endswith('"') and trimmed.count('"') == 2:
            trimmed = trimmed[1:-1].strip()

        return trimmed
