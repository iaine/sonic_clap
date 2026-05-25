import laion
import mclap
import sys  
 
def process_input(input_text):  
    return f"Python processed: {input_text.upper()}"  
 
if __name__ == "__main__":  
    # Read input from Electron (via stdin)  
    input_text = sys.stdin.readline().strip()  
    # Process and send output back (via stdout)  
    result = process_input(input_text)  
    print(result)  
    sys.stdout.flush()  # Ensure output is sent immediately 