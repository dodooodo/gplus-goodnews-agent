from google.genai import types
from google import genai
import app.prompts as prompts


client = genai.Client(api_key='AIzaSyA8KvZoc33OcXY4bqr7n5pOEKLKAfuKliE')


# OpenAI API 請求封裝
async def analyze_posts(post_text: str, language: str) -> str:
    prompt = prepare_prompt(post_text, language)
    # print(prompt)
    response = await call_openai_api(prompt)
    return response


# 準備 ChatGPT 請求的提示（Prompt）
def prepare_prompt(post_text: str, language: str) -> str:
    if language == "ch":
        return prompts.LIPromptCHEN.format(article_content=post_text)
    elif language == "en":
        return prompts.LIPromptEN.format(article_content=post_text)
    else:
        raise ValueError(f"Unsupported language: {language}")


# 呼叫 OpenAI API
async def call_openai_api(prompt: str) -> str:
    response = await client.aio.models.generate_content(
          model='gemini-2.0-flash',
          contents=prompt,
          config=types.GenerateContentConfig(
              system_instruction=
                [
                  prompts.LIInstruction
                ]
          ),
      )
    return response.text
