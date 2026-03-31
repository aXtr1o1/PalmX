import pandas as pd
import os
import subprocess

LEADS_PATH = "/Volumes/ReserveDisk/codeBase/PalmX/runtime/leads/leads.csv"
WORK_DIR = "/Volumes/ReserveDisk/codeBase/PalmX/runtime/leads"

def parallel_enrich():
    df = pd.read_csv(LEADS_PATH)
    num_workers = 4
    chunk_size = len(df) // num_workers + 1
    
    processes = []
    for i in range(num_workers):
        start = i * chunk_size
        end = (i + 1) * chunk_size
        chunk = df.iloc[start:end]
        
        chunk_in = os.path.join(WORK_DIR, f"chunk_{i}_in.csv")
        chunk_out = os.path.join(WORK_DIR, f"chunk_{i}_out.csv")
        chunk.to_csv(chunk_in, index=False)
        
        proc = subprocess.Popen(["python3", os.path.join(WORK_DIR, "worker_enrich.py"), chunk_in, chunk_out])
        processes.append((proc, chunk_in, chunk_out))
        print(f"Started worker {i} for leads {start} to {min(end, len(df))}")

    print("All workers started. Waiting for completion...")
    for proc, cin, cout in processes:
        proc.wait()
    
    print("Merging results...")
    final_dfs = []
    for i in range(num_workers):
        final_dfs.append(pd.read_csv(os.path.join(WORK_DIR, f"chunk_{i}_out.csv")))
    
    final_df = pd.concat(final_dfs)
    final_df.to_csv(LEADS_PATH, index=False)
    final_df.to_csv(LEADS_PATH.replace("leads.csv", "leads_seed.csv"), index=False)
    
    # Clean up
    for i in range(num_workers):
        os.remove(os.path.join(WORK_DIR, f"chunk_{i}_in.csv"))
        os.remove(os.path.join(WORK_DIR, f"chunk_{i}_out.csv"))
    
    print("Parallel enrichment complete.")

if __name__ == "__main__":
    parallel_enrich()
