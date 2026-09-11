import os
import json
from abc import ABC, abstractmethod
from google import genai
from google.genai import types

class LLMProvider(ABC):
    @abstractmethod
    async def extract_case_metadata(self, text: str) -> dict:
        pass
        
    @abstractmethod
    async def generate_summary(self, context: str, language: str = "english") -> str:
        pass
        
    @abstractmethod
    async def answer_question(self, question: str, context: str) -> str:
        pass

class GeminiLLMProvider(LLMProvider):
    def __init__(self):
        api_key = os.getenv("GEMINI_LLM_API_KEY") or os.getenv("GEMINI_EMBEDDING_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.model = os.getenv("GEMINI_LLM_MODEL", "gemini-1.5-flash")
        # Instantiate explicitly with the LLM API key
        self.client = genai.Client(api_key=api_key) if api_key else genai.Client()

    async def extract_case_metadata(self, text: str) -> dict:
        prompt = """
        Extract case information from the following text.
        Output must be valid JSON with the following structure:
        {
          "court": null,
          "case_type": null,
          "case_number": null,
          "case_year": null,
          "title": null,
          "petitioners": [],
          "respondents": [],
          "judges": [],
          "date_of_order": null,
          "date_of_judgment": null,
          "advocates": [],
          "sections": [],
          "articles": [],
          "acts": [],
          "rules": [],
          "relief_sought": null,
          "relief_granted": null,
          "outcome": null
        }
        If information isn't present, use null or []. Never guess.
        """
        
        import asyncio
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=[prompt, text],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    )
                )
                return json.loads(response.text)
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    print(f"Hit Gemini Rate Limit in metadata extraction. Waiting 30s (Attempt {attempt+1}/{max_retries})...")
                    await asyncio.sleep(30)
                else:
                    print(f"Error in metadata extraction: {e}")
                    return {}
        return {}

    async def generate_summary(self, context: str) -> str:
        prompt = f"""
        Based on the provided case text, generate a highly detailed and comprehensive case summary formatted in clean Markdown.
        IMPORTANT: Your summary must be incredibly thorough, equivalent to a 2 to 3 page long document. 
        Cover ALL important data, arguments, evidence, and court reasonings in extreme depth. Do not miss any details.
        
        Organize the summary using clear Markdown headings (e.g., ## Executive Summary, ## Facts, ## Court's Reasoning, etc).
        Every important section should have internal page references like [p. 17].
        
        Text:
        {context}
        """
        import asyncio
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=[prompt, context]
                )
                return response.text
            except Exception as e:
                error_msg = str(e)
                if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                    print(f"Hit Gemini Rate Limit in summary generation. Waiting 30s (Attempt {attempt+1}/{max_retries})...")
                    await asyncio.sleep(30)
                else:
                    print(f"Error in summary generation: {e}")
                    return "Failed to generate summary."
        return "Failed to generate summary."

    async def answer_question(self, question: str, context: str) -> str:
        system_instruction = """
        You are analyzing an uploaded legal document.
        Use ONLY the evidence provided in the context.
        Do not invent facts. Do not invent page numbers. Do not invent citations.
        Do not treat allegations as findings.
        Clearly distinguish petitioner arguments, respondent arguments, documentary statements, and court findings.
        If the requested information is not supported by the supplied evidence, say: "The answer was not found in the uploaded document."
        If evidence is conflicting, explain the conflict.
        Every important factual statement must have a source page based on the chunk metadata.
        """
        
        prompt = f"""
        Evidence:
        {context}
        
        Question:
        {question}
        """
        
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction
            )
        )
        return response.text

class GroqLLMProvider(LLMProvider):
    def __init__(self):
        from groq import Groq
        api_key = os.getenv("GROQ_API_KEY")
        self.model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        self.client = Groq(api_key=api_key) if api_key else Groq()

    def _clean_parse_json(self, content: str) -> dict:
        import re
        try:
            return json.loads(content)
        except Exception:
            pass
        cleaned = re.sub(r"^```(?:json)?\s*", "", content, flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()
        try:
            return json.loads(cleaned)
        except Exception:
            pass
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError(f"No valid JSON object found in response: {content[:100]}...")

    async def extract_case_metadata(self, text: str) -> dict:
        prompt = f"""
        Extract case information from the following text.
        Output must be valid JSON with the following structure:
        {{
          "court": null,
          "case_type": null,
          "case_number": null,
          "case_year": null,
          "title": null,
          "petitioners": [],
          "respondents": [],
          "judges": [],
          "date_of_order": null,
          "date_of_judgment": null,
          "advocates": [],
          "sections": [],
          "articles": [],
          "acts": [],
          "rules": [],
          "relief_sought": null,
          "relief_granted": null,
          "outcome": null
        }}
        If information isn't present, use null or []. Never guess.
        
        Text:
        {text}
        """
        
        messages = [
            {"role": "system", "content": "You are a legal AI assistant. Output ONLY a raw, valid JSON object matching the requested schema without markdown formatting or surrounding text."},
            {"role": "user", "content": prompt}
        ]
        
        raw_content = ""
        for attempt in range(2):
            try:
                response = self.client.chat.completions.create(
                    messages=messages,
                    model=self.model,
                    response_format={"type": "json_object"}
                )
                raw_content = response.choices[0].message.content or ""
                return self._clean_parse_json(raw_content)
            except Exception as e:
                err_msg = str(e)
                print(f"Groq Metadata Error (attempt {attempt+1}/2): {e}")
                if "tokens" in err_msg.lower() or "rate_limit" in err_msg.lower():
                    print("Groq token limit exceeded for metadata. Falling back to Gemini...")
                    fallback = GeminiLLMProvider()
                    return await fallback.extract_case_metadata(text)
                if attempt == 0:
                    messages.append({"role": "assistant", "content": raw_content})
                    messages.append({"role": "user", "content": "Your response was not valid JSON. Return ONLY the valid JSON object without markdown or extra text."})
                else:
                    return {}
        return {}

    async def generate_summary(self, context: str, language: str = "english") -> str:
        # Cap context to ~13k characters (approx 3,250 tokens) to safely fit within Groq 8,000 TPM limit
        if len(context) > 13000:
            summary_context = context[:10000] + "\n\n...[Middle section omitted for context length]...\n\n" + context[-3000:]
        else:
            summary_context = context

        # Build language-specific instruction
        lang_lower = language.lower()
        if lang_lower == "gujarati":
            lang_instruction = (
                "LANGUAGE: Write the ENTIRE summary in Gujarati script (ગુજરાતી). "
                "Use Gujarati for all headings, explanations, arguments, and court reasoning. "
                "Only keep proper nouns (names, case numbers, court names) in their original form. "
                "Do NOT write in English."
            )
        elif lang_lower == "hindi":
            lang_instruction = (
                "LANGUAGE: Write the ENTIRE summary in Hindi (हिंदी) using Devanagari script. "
                "Use Hindi for all headings, explanations, arguments, and court reasoning. "
                "Only keep proper nouns (names, case numbers, court names) in their original form. "
                "Do NOT write in English."
            )
        else:
            lang_instruction = (
                "LANGUAGE: Write the entire summary in clear, professional English."
            )

        prompt = f"""
        Based on the provided case text, generate a highly detailed and comprehensive case summary formatted in clean Markdown.
        IMPORTANT: Your summary must be incredibly thorough, equivalent to a 2 to 3 page long document. 
        Cover ALL important data, arguments, evidence, and court reasonings in extreme depth. Do not miss any details.
        
        {lang_instruction}
        
        Organize the summary using clear Markdown headings (e.g., ## Executive Summary, ## Facts, ## Court's Reasoning, etc).
        Every important section should have internal page references like [p. 17].
        
        Text:
        {summary_context}
        """
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a multilingual legal AI assistant fluent in English, Gujarati, and Hindi. You output detailed Markdown summaries in the language requested by the user."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                max_tokens=2500
            )
            return response.choices[0].message.content or "Failed to generate summary."
        except Exception as e:
            print(f"Groq Summary Error: {e}")
            return f"Failed to generate summary: {e}"

    async def answer_question(self, question: str, context: str) -> str:
        system_instruction = """
        You are a bilingual legal AI assistant analyzing an uploaded legal document (English / Gujarati / Hindi).
        Use ONLY the evidence provided in the context.
        Do not invent facts. Do not invent page numbers. Do not invent citations.
        Do not treat allegations as findings.
        If the user asks in Gujarati or if the context contains Gujarati legal evidence, answer in Gujarati (or bilingual Gujarati + English) while preserving exact original terms.
        Clearly distinguish petitioner arguments, respondent arguments, documentary statements, and court findings.
        If the requested information is not supported by the supplied evidence, say: "The answer was not found in the uploaded document."
        If evidence is conflicting, explain the conflict.
        Every important factual statement must have a source page based on the chunk metadata.
        """
        
        prompt = f"""
        Evidence:
        {context}
        
        Question:
        {question}
        """
        
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            model=self.model
        )
        return response.choices[0].message.content

class NvidiaLLMProvider(LLMProvider):
    def __init__(self):
        from openai import OpenAI
        api_key = os.getenv("NVIDIA_API_KEY")
        self.model = "meta/llama-3.2-11b-vision-instruct"
        self.client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )

    async def extract_case_metadata(self, text: str) -> dict:
        prompt = f"""
        Extract case information from the following text.
        Output must be valid JSON with the following structure:
        {{
          "court": null,
          "case_type": null,
          "case_number": null,
          "case_year": null,
          "title": null,
          "petitioners": [],
          "respondents": [],
          "judges": [],
          "date_of_order": null,
          "date_of_judgment": null,
          "advocates": [],
          "sections": [],
          "articles": [],
          "acts": [],
          "rules": [],
          "relief_sought": null,
          "relief_granted": null,
          "outcome": null
        }}
        If information isn't present, use null or []. Never guess.
        
        Text:
        {text}
        """
        
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a legal AI assistant. You must output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model,
                response_format={"type": "json_object"}
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            print(f"Nvidia Metadata Error: {e}")
            return {}

    async def generate_summary(self, context: str) -> str:
        prompt = f"""
        Based on the provided case text, generate a highly detailed and comprehensive case summary formatted in clean Markdown.
        IMPORTANT: Your summary must be incredibly thorough, equivalent to a 2 to 3 page long document. 
        Cover ALL important data, arguments, evidence, and court reasonings in extreme depth. Do not miss any details.
        
        Organize the summary using clear Markdown headings (e.g., ## Executive Summary, ## Facts, ## Court's Reasoning, etc).
        Every important section should have internal page references like [p. 17].
        
        Text:
        {context}
        """
        try:
            response = self.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are a legal AI assistant. You must output a detailed Markdown summary."},
                    {"role": "user", "content": prompt}
                ],
                model=self.model
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Nvidia Summary Error: {e}")
            return "Failed to generate summary."

    async def answer_question(self, question: str, context: str) -> str:
        system_instruction = """
        You are analyzing an uploaded legal document.
        Use ONLY the evidence provided in the context.
        Do not invent facts. Do not invent page numbers. Do not invent citations.
        Do not treat allegations as findings.
        Clearly distinguish petitioner arguments, respondent arguments, documentary statements, and court findings.
        If the requested information is not supported by the supplied evidence, say: "The answer was not found in the uploaded document."
        If evidence is conflicting, explain the conflict.
        Every important factual statement must have a source page based on the chunk metadata.
        """
        
        prompt = f"""
        Evidence:
        {context}
        
        Question:
        {question}
        """
        
        response = self.client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            model=self.model
        )
        return response.choices[0].message.content
