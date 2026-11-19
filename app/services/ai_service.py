# import os
#
# from dotenv import load_dotenv
# from openai import OpenAI
#
#
# load_dotenv()
#
# client = OpenAI(
#     api_key=os.getenv("OPENAI_API_KEY")
# )
#
#
# class AIService:
#
#     def generate_linkedin_post(
#         self,
#         topic: str,
#         category: str,
#         problem: str | None,
#         what_i_learned: str,
#         project: str | None,
#         lesson: str | None
#     ):
#
#         prompt = f"""
# You are helping a software engineer document their learning
# journey on LinkedIn.
#
# Create an authentic LinkedIn post based ONLY on the information
# provided below.
#
# Topic:
# {topic}
#
# Category:
# {category}
#
# Problem:
# {problem}
#
# What I learned:
# {what_i_learned}
#
# Project:
# {project}
#
# Lesson:
# {lesson}
#
# Requirements:
# - Write in first person.
# - Sound like a software engineer documenting their journey.
# - Do not exaggerate achievements.
# - Do not invent experiences.
# - Start with a strong but natural hook.
# - Explain the technical concept clearly.
# - Include what I struggled with and what I learned when appropriate.
# - Keep it conversational and professional.
# - Avoid excessive emojis.
# - Avoid generic motivational language.
# - End with a thoughtful question or takeaway.
# """
#
#         response = client.responses.create(
#             model="gpt-5.6",
#             input=prompt
#         )
#
#         api_key = os.getenv("OPENAI_API_KEY")
#
#         print("API KEY LOADED:", bool(api_key))
#
#         return response.output_text


# import os
# from dotenv import load_dotenv
#
# load_dotenv()
#
# api_key = os.getenv("OPENAI_API_KEY")
#
# print("API KEY EXISTS:", bool(api_key))
# print("API KEY PREFIX:", api_key[:7] if api_key else None)
#
# from openai import OpenAI
#
# client = OpenAI(api_key=api_key)


import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


class AIService:

    def generate_linkedin_post(
        self,
        topic: str,
        category: str,
        problem: str | None,
        what_i_learned: str,
        project: str | None,
        lesson: str | None
    ):
        prompt = f"""
You are helping a software engineer document their
learning journey on LinkedIn.

Create an authentic LinkedIn post using ONLY the
information provided below.

Topic:
{topic}

Category:
{category}

Problem:
{problem}

What I learned:
{what_i_learned}

Project:
{project}

Lesson:
{lesson}

Requirements:
- Write in first person.
- Sound authentic and conversational.
- Keep the tone professional.
- Explain the technical concept clearly.
- Do not invent experiences or achievements.
- Do not exaggerate.
- Avoid generic motivational language.
- Avoid excessive emojis.
- Start with an interesting hook.
- End with a useful takeaway or thoughtful question.
"""

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {   "role": "user",
                    "content": prompt}
            ]
        )

        return response.choices[0].message.content