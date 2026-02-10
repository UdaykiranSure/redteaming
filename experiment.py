from attacker import  MistralAttacker
from attack import generate_attack_prompts, adaptive_attack_loop
from system_prompts import SYSTEM_PROMPTS       
from target import TargetModel
import json

attacker = MistralAttacker(api_key="zZgtn5sGizW1ilh2VckjFYykE0DenE3v")
target = TargetModel(base_url="http://localhost:8000/v1/chat/completions")

for attack_type in ("direct", "role_play", "cot_hijacking"):
        
        system_prompt = SYSTEM_PROMPTS[attack_type]
        seed_prompts = generate_attack_prompts(attacker, system_prompt)

        results = []
        for p in seed_prompts:
            result = adaptive_attack_loop(
                attacker,
                target,
                system_prompt,
                p
            )
            results.append(result)

        filename = f'{attack_type}_results.json'
        with open(filename, 'w') as json_file:
            json.dump(results, json_file, indent=4)
