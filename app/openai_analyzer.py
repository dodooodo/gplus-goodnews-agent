from openai import AsyncOpenAI
import app.prompts as prompts
import dotenv


client = AsyncOpenAI(
    api_key=dotenv.dotenv_values(".env")["OPENAI_API_KEY"],
    )


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
    response = await client.responses.create(
        model="gpt-4.1-nano",
        instructions=prompts.LIInstruction,
        input=prompt,
        # prompt=prompt,
        # max_tokens=1000,
        # temperature=0.7,
        # top_p=1,
        # frequency_penalty=0,
        # presence_penalty=0,
    )
    # response = response.choices[0].text.strip()
    # print(type(response.output_text))
    return response.output_text
