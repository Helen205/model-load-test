from locust import HttpUser, task, between
import random
import time
from datetime import datetime
import gevent
from gevent import monkey
import pandas as pd
import os
from threading import Lock, Event
monkey.patch_all()

class ChatUser(HttpUser):
    wait_time = between(1, 2)
    test_results = []
    MAX_REQUESTS = 50
    _lock = Lock()
    test_running = True
    stop_event = Event()  
    
    def on_start(self):
        self.start_time = datetime.now()
        
    def save_results(self):
        try:
            if self.test_results:
                new_df = pd.DataFrame(self.test_results)
                
                columns = [
                    'load_balancer',
                    'ollama_num',
                    'context_length',
                    'response_time',
                    'model parameters',
                    'model',
                    'num_predict',
                    'users',
                    'model_size',
                    'RAM',
                    'GPU',
                    'question',
                    'response'
                ]
                
                new_df = new_df[columns]
                
                desktop = r"C:\Users\Helen\Documents\GitHub\model-load-test"
                

                excel_filename = os.path.join(desktop, f"load_test_results.xlsx")
                

                csv_filename = os.path.join(desktop, f"load_test_results.csv")
                
                try:
                    if os.path.exists(csv_filename):
                        try:
                            existing_csv_df = pd.read_csv(csv_filename)
                            combined_csv_df = pd.concat([existing_csv_df, new_df], ignore_index=True)
                        except:
                            print("Could not read existing CSV file, creating new one")
                            combined_csv_df = new_df
                    else:
                        combined_csv_df = new_df
                    
                    combined_csv_df.to_csv(csv_filename, index=False)
                    print(f"Results saved to CSV: {csv_filename}")
                    
                    if os.path.exists(excel_filename):
                        try:
                            
                            existing_df = pd.read_excel(excel_filename, engine='openpyxl')
                            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                        except:
                            combined_df = new_df
                    else:
                        combined_df = new_df
                    
                    
                    combined_df.to_excel(excel_filename, index=False, engine='openpyxl')
                    print(f"Results saved to Excel: {excel_filename}")
                    print(f"Total requests processed: {self.environment.stats.total.num_requests}")
                    print(f"Total rows saved: {len(combined_df)}")
                    
                except Exception as e:
                    print(f"Error handling files: {str(e)}")
                    if not os.path.exists(csv_filename):
                        new_df.to_csv(csv_filename, index=False)
                        print(f"Results saved to CSV as fallback: {csv_filename}")
                
        except Exception as e:
            print(f"Error saving results: {str(e)}")
            print("\nTest Results:")
            for result in self.test_results:
                print(result)
    
    def should_stop_test(self):
        with self._lock:
            if self.environment.stats.total.num_requests >= self.MAX_REQUESTS:
                if not self.stop_event.is_set():  
                    self.test_running = False
                    print("\nReached maximum request limit. Stopping the test...")
                    self.save_results()
                    self.stop_event.set()
                    try:
                        self.environment.runner.quit()
                    except:
                        pass
                return True
            return False
    
    def on_stop(self):
        if not self.stop_event.is_set():
            self.test_running = False
            self.save_results()
            self.stop_event.set()
            try:
                self.environment.runner.quit()
            except:
                pass
    
    @task(1)
    def parallel_chat(self):
        if not self.test_running or self.should_stop_test():
            return
            
        questions = [
            "What is your name?",
            "How are you today?",
            "What is the weather like?",
            "What is 2+2?",
            "What is the capital of France?",
            "How many days in a week?",
            "What color is the sky?",
            "What is your favorite color?",
            "Do you like pizza?",
            "What is your favorite food?",
            "What is your job?",
            "Can you speak English?"
        ]
        
        threads = []
        for _ in range(2):
            if not self.test_running or self.should_stop_test():
                break
                
            question = random.choice(questions)
            thread = gevent.spawn(self.send_chat_request, question)
            threads.append(thread)
            time.sleep(0.5)
        
        for thread in threads:
            if self.test_running:
                thread.join()
    
    def send_chat_request(self, question):
        if not self.test_running or self.should_stop_test():
            return
            
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries and self.test_running:
            if self.should_stop_test():
                return
                
            try:
                chat_data = {
                    "model": "qwen2.5:1.5b",
                    "prompt": question,
                    "stream": False,
                    "options": {
                        "num_ctx": 2048,
                        "num_predict": 1024
                    }
                }
                
                start_time = time.time()
                with self.client.post("/api/ip-hash/api/generate", json=chat_data, catch_response=True) as response:
                    end_time = time.time()
                    duration = (end_time - start_time) * 1000
                    
                    current_count = self.environment.stats.total.num_requests
                    print(f"\nRequest count: {current_count}/{self.MAX_REQUESTS}")
                    print(f"Response status: {response.status_code}")

                    if response.status_code == 0:
                        raise ConnectionError("Connection failed or refused")

                    try:
                        response_json = response.json()
                        response_text = response_json.get("response", "")
                    except ValueError as e:
                        print(f"JSON parsing error: {str(e)}")
                        retry_count += 1
                        continue

                    if response.status_code == 200:
                        if not self.test_running:
                            return
                        response.success()
                        result = pd.Series({
                            'load_balancer': 'ip-hash',
                            'ollama_num': 4,
                            'context_length': 2048,
                            'response_time': float(duration),
                            'model parameters': '1.54B',
                            'model': 'qwen2.5:1.5b',
                            'num_predict': 1024,
                            'users': 150,
                            'model_size': '986MB',
                            'RAM': 'AMD Ryzen 7 8845HS',
                            'GPU': 'Radeon 780M Graphics(8 CPUs)',
                            'question': question,
                            'response': response_text
                        })
                        self.test_results.append(result.to_dict())
                        print(f"Question: {question[:50]}...")
                        print(f"Response: {response_text}...")
                        print(f"Response Time: {duration:.2f}ms")
                        return
                    else:
                        print(f"Error Response Time: {duration:.2f}ms")
                        retry_count += 1
                        if response.status_code == 429:
                            wait_time = 2 ** retry_count
                            print(f"Rate limit hit, waiting {wait_time} seconds...")
                            time.sleep(wait_time)
                        
            except Exception as e:
                if not self.test_running:
                    return
                print(f"Exception occurred: {str(e)}")
                retry_count += 1
                time.sleep(1)

