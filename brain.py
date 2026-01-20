from openai import OpenAI
import json

# Initialize the client (Replace with your key or use an environment variable)
client = OpenAI(api_key="YOUR_OPENAI_API_KEY")

def rank_my_tasks(task_list):
    """
    Sends the Canvas tasks to OpenAI to be ranked by priority.
    """
    prompt = f"""
    You are an academic success coach. Rank the following Canvas assignments based on:
    1. Due Date (urgency)
    2. Points Possible (importance/weight)
    
    Assignments: {json.dumps(task_list)}
    
    Return the output as a clean numbered list. For each, explain WHY it is ranked there.
    """

    response = client.chat.completions.create(
        model="gpt-4o",  # or "gpt-4o-mini" for lower cost
        messages=[
            {"role": "system", "content": "You are a helpful academic advisor focused on reducing student stress."},
            {"role": "user", "content": prompt}
        ]
    )
    
    return response.choices[0].message.content
