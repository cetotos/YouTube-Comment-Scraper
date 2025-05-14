import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
import threading
from googleapiclient.discovery import build
import time

# Function to get video ID from YouTube link
def get_video_id(url):
    if "shorts/" in url:
        return url.split("shorts/")[-1].split("?")[0]
    elif "v=" in url:
        return url.split("v=")[-1].split("&")[0]
    return url.strip()

# Function to scrape comments
def scrape_comments(video_id, youtube):
    comments = []
    next_page_token = None

    while True:
        response = youtube.commentThreads().list(
            part="snippet",
            videoId=video_id,
            maxResults=100,
            pageToken=next_page_token,
            textFormat="plainText"
        ).execute()

        for item in response["items"]:
            comment = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            comments.append(comment)

        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break

    return comments

# Function to run the scraper
def run_scraper(input_path, output_path, api_key, status_box, progress_bar, progress_label, cancel_event):
    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
        with open(input_path, "r", encoding="utf-8") as f:
            video_urls = [line.strip() for line in f if line.strip()]
    except Exception as e:
        messagebox.showerror("Error", f"Failed to read input file:\n{e}")
        return

    total_comments = 0
    total_videos = len(video_urls)

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            for idx, url in enumerate(video_urls):
                if cancel_event.is_set():
                    status_box.insert(tk.END, "\nScraping cancelled by user.\n")
                    status_box.see(tk.END)
                    return  # Prevent "Done" message from being printed after cancellation

                video_id = get_video_id(url)
                status_box.insert(tk.END, f"\nFetching: {video_id}...\n")
                status_box.see(tk.END)

                try:
                    comments = scrape_comments(video_id, youtube)
                    count = len(comments)
                    total_comments += count
                    for comment in comments:
                        f.write(comment + "\n")
                    status_box.insert(tk.END, f"{count} comments saved from {url}\n")
                except Exception as e:
                    # Handle commentsDisabled error
                    if 'commentsDisabled' in str(e):
                        status_box.insert(tk.END, f"Failed, comments disabled on video: {url}\n")
                    else:
                        status_box.insert(tk.END, f"Failed to fetch {url}: {e}\n")
                status_box.see(tk.END)

                # Update progress bar
                progress = (idx + 1) / total_videos * 100
                progress_bar['value'] = progress
                progress_label.config(text=f"{int(progress)}% complete")
                root.update_idletasks()

        if not cancel_event.is_set():  # Only print this if the operation wasn't canceled
            status_box.insert(tk.END, f"\nDone. Total comments fetched: {total_comments}\n")
            status_box.insert(tk.END, f"Saved to: {output_path}\n")
            status_box.see(tk.END)
    except Exception as e:
        messagebox.showerror("Error", f"Failed during writing or scraping:\n{e}")

# Function to choose input file
def choose_input_file():
    file_path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
    if file_path:
        input_entry.delete(0, tk.END)
        input_entry.insert(0, file_path)

# Function to choose output file
def choose_output_file():
    file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")])
    if file_path:
        output_entry.delete(0, tk.END)
        output_entry.insert(0, file_path)

# Function to start scraping
def start_scraping():
    input_path = input_entry.get()
    output_path = output_entry.get()
    api_key = api_key_entry.get()

    if not all([input_path, output_path, api_key]):
        messagebox.showwarning("Missing Info", "Please provide all inputs: API key, input file, and output file.")
        return

    progress_bar['value'] = 0
    progress_label.config(text="0% complete")
    
    cancel_event.clear()
    threading.Thread(target=run_scraper, args=(input_path, output_path, api_key, status_box, progress_bar, progress_label, cancel_event), daemon=True).start()

# Function to cancel the scraping
def cancel_scraping():
    cancel_event.set()
    status_box.insert(tk.END, "\nScraping cancelled by user.\n")
    status_box.see(tk.END)

# GUI setup
root = tk.Tk()
root.title("YouTube Comment Scraper")

main_frame = tk.Frame(root)
main_frame.pack(padx=20, pady=20)

# API Key
tk.Label(main_frame, text="YouTube API Key:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
api_key_entry = tk.Entry(main_frame, width=60)
api_key_entry.grid(row=0, column=1, padx=5, pady=5)

# Input file
tk.Label(main_frame, text="Input Links File:").grid(row=1, column=0, sticky="e", padx=5)
input_entry = tk.Entry(main_frame, width=60)
input_entry.grid(row=1, column=1, padx=5)
tk.Button(main_frame, text="Browse", command=choose_input_file).grid(row=1, column=2)

# Output file
tk.Label(main_frame, text="Output Comments File:").grid(row=2, column=0, sticky="e", padx=5)
output_entry = tk.Entry(main_frame, width=60)
output_entry.grid(row=2, column=1, padx=5)
tk.Button(main_frame, text="Save As", command=choose_output_file).grid(row=2, column=2)

# Scrape button
tk.Button(main_frame, text="Start Scraping", command=start_scraping, bg="#4CAF50", fg="white").grid(row=3, column=0, columnspan=3, pady=10)

# Progress bar
progress_bar = ttk.Progressbar(main_frame, orient="horizontal", length=500, mode="determinate")
progress_bar.grid(row=4, column=0, columnspan=3, padx=10, pady=5)

# Progress label
progress_label = tk.Label(main_frame, text="0% complete", font=("Helvetica", 10))
progress_label.grid(row=5, column=0, columnspan=3, padx=10, pady=5)

# Status output
status_box = tk.Text(root, width=80, height=20)
status_box.pack(padx=20, pady=(0, 20))

# Cancel button
cancel_event = threading.Event()
cancel_button = tk.Button(root, text="Cancel", command=cancel_scraping, bg="#FF6347", fg="white")
cancel_button.pack(pady=10)

root.mainloop()
