import inspect
import json
import os
import keyboard
import ollama
import Handler.debugger as dbg

debug = dbg.debug


class ChatBot:

    def __init__(self, name="bot", desc="An Entity", task=None):
        self.model = "phi3"
        self.name = name
        self.description = desc
        self.task = task or "just chat with the user"
        self.response = None
        self.output_chunk = None

        # System rules scaled down to purely rely on your inputs
        self.system_instructions = (
            f"Identity Name: {self.name}\n"
            f"Description: {self.description}\n"
            f"Current Task: {self.task}\n"
            f"CRITICAL CONSTRAINT: You must embody this identity completely. "
            f"Reply in exactly 1 or 2 sentences. Do not explain your role."
        )

        self.Banned_Key_Word = [
            "###", "SYSTEM INSTRUCTIONS", "CRITICAL CONSTRAINT", 
            "CONVERSATION HISTORY", "NEXT RESPONSE", "Assistant:", 
            f"{self.name}:", "User:"
        ]

        # Conversation log tracking array
        self.history = []
        
        # Max message capacity (6 items = 3 user inputs + 3 entity replies)
        self.max_history = 20
        self.max_user_input = 300

        # Force client to use direct local IPv4 to bypass Windows proxy routing drops
        self.client = ollama.Client(host="http://127.0.0.1:11434")

        # LIGHTWEIGHT MEMORY: Load long-term facts from a local flat file
        # Get the exact folder where this Python file lives
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Safely join it to relative path
        self.memory_file = os.path.abspath(os.path.join(script_dir, "../data-folder/user_facts.json"))
        self.long_term_facts = self._load_facts()

    def _load_facts(self):
        """Load known facts about the user from a simple JSON file."""
        try:
            with open(self.memory_file, "r") as f:
                return json.load(f)
        except FileNotFoundError as fileError:
            debug("Error", f"Error FileNotFound: {fileError}")
            return []  # Start empty if no file exists yet

    def _sanatise_response(self):
        """Clean data on the fly and yield chunks one-by-one to preserve streaming."""
        self.output_chunk = []
        try:
            for chunk in self.response:
                part = chunk.get('response') or chunk.get('response_part') or ''

                for keyword in self.Banned_Key_Word:
                    part = part.replace(keyword, "")

                self.output_chunk.append(part)
                yield part  # Yields the token instantly without draining the rest of the stream

            # Save to history dynamically using the assigned NAME
            full_output = "".join(self.output_chunk)
            self.history.append(f"{self.name}: {full_output.strip()}")
            
            debug(f"function {inspect.currentframe().f_code.co_name}", f"Output: {full_output}", f"Output chunk: {self.output_chunk}")
            
        except Exception as e:
            debug("Error while processing stream chunks", e)
            raise e
            
        finally:
            # This block runs ONLY after the streaming loop has entirely finished
            if len(self.history) > self.max_history:
                self.history.pop(0)

    def get_response(self, raw_user_input=None):
        if not raw_user_input:
            raw_user_input = input("Prompt here> ")

        # ANTI-JAILBREAK CLEANING: Strip out markdown headers and system keywords
        # This stops the user from injecting fake instructions into history block
        clean_input = raw_user_input.strip()
        dangerous_keywords = self.Banned_Key_Word
        max_input = self.max_user_input
        
        for keyword in dangerous_keywords:
            clean_input = clean_input.replace(keyword, "")

        # If the user tries to paste a massive text wall to break the bot, truncate it
        if len(clean_input) > max_input:
            clean_input = clean_input[:max_input] + "... [input truncated for safety]"

        # Log the completely safe, cleaned text into the memory list
        self.history.append(f"User: {clean_input.strip()}")
        
        # Prune old context if history bounds are exceeded
        if len(self.history) > self.max_history:
            self.history.pop(0)

        # Rebuild full conversation history prompt context
        facts_block = "\n".join([f"- {fact}" for fact in self.long_term_facts]) if self.long_term_facts else "- No prior facts known yet."

        history_block = "\n".join(self.history)
        
        full_prompt = (
            f"### SYSTEM INSTRUCTIONS\n{self.system_instructions}\n\n"
            f"### KNOWN FACTS (LONG-TERM MEMORY)\n{facts_block}\n\n"
            f"### CONVERSATION HISTORY\n{history_block}\n\n"
            f"### NEXT RESPONSE:\n{self.name}:"
        )

        # Call generate via the direct IPv4 client connection object
        response = self.client.generate(
            model=self.model, prompt=full_prompt, stream=True, keep_alive=True
        )

        try:
            # Loop until getting response back.
            while not response:
                debug(
                    "Function chat", 
                    "Waiting for response...",
                )
                continue

            self.response = response
            debug(
                "Function chat",
                f"User input: {clean_input}",
                f"Response: {response}",
            )
            
            return self.response
        except Exception as Error:
            # If error  tells the debugger there's an error and return nothing.
            debug(
                "Function chat",
                f"Unexpected Error: {Error}"
            )

            return None


    def show_output(self, cleaned_stream):
        """Handles only display logic, animating tokens as they are yielded."""
        print(f"{self.name.capitalize()}: ", end="", flush=True)
        
        for part in cleaned_stream:
            print(part, end="", flush=True)  # This creates the typewriter animation
            
        print()  # Final clean line break

    def chat(self):
        try:
            while True:
                print("\nPress 'esc' to leave")
                
                if keyboard.is_pressed("esc"):
                    print("leaving...")
                    break
                
                self.get_response()
                
                # Capture the generator wrapper without running it yet
                cleaned_stream = self._sanatise_response()
                
                # Pass the generator to the display function to animate
                self.show_output(cleaned_stream)

        except Exception as e:
            debug("Error in function chat", f"Errortype: {e}")
            print("\nSession halted due to connection disruption.")
            return
