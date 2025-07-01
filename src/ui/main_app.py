import customtkinter as ctk
import os
import configparser
import threading
import queue

from ..game_engine.card import Card
from ..game_engine.deck import Deck, load_meta_decks
from ..optimizer.runner import run_ga

# Get the project root for file path access, but don't modify sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Project Oracle")
        self.geometry("500x350")
        self.last_results = None

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(self, text="Project Oracle - Lorcana Deck Optimizer", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.welcome_label = ctk.CTkLabel(self, text="Welcome! Click 'Run Optimizer' to begin.", font=ctk.CTkFont(size=12))
        self.welcome_label.grid(row=1, column=0, padx=20, pady=10)

        self.status_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=10))
        self.status_label.grid(row=2, column=0, padx=20, pady=0)

        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(side="left", expand=True, fill="x", padx=(0, 10))
        self.progress_bar.set(0)
        self.fitness_label = ctk.CTkLabel(self.progress_frame, text="Best Fitness: N/A", font=ctk.CTkFont(size=12))
        self.fitness_label.pack(side="left")
        self.progress_frame.grid_remove()

        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.grid(row=4, column=0, padx=20, pady=20, sticky="s")
        self.button_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.run_button = ctk.CTkButton(self.button_frame, text="Run Optimizer", command=self.run_optimizer)
        self.run_button.grid(row=0, column=0, padx=5)

        self.view_results_button = ctk.CTkButton(self.button_frame, text="View Results", command=self.show_results_window)
        self.view_results_button.grid(row=0, column=1, padx=5)
        self.view_results_button.grid_remove()

        self.exit_button = ctk.CTkButton(self.button_frame, text="Exit", command=self.destroy)
        self.exit_button.grid(row=0, column=2, padx=5)

    def run_optimizer(self):
        self.run_button.configure(state="disabled")
        self.view_results_button.grid_remove()
        self.status_label.configure(text="Loading cards and decks...")
        self.update_idletasks()

        db_path = os.path.join(project_root, 'lorcana.db')
        all_cards = Card.load_all_cards(db_path)
        if not all_cards:
            self.status_label.configure(text="Error: Failed to load cards.")
            self.run_button.configure(state="normal")
            return

        meta_decks = load_meta_decks(db_path, all_cards)
        if not meta_decks:
            self.status_label.configure(text="Error: Failed to load meta decks.")
            self.run_button.configure(state="normal")
            return

        self.status_label.configure(text="Starting genetic algorithm...")
        self.progress_frame.grid()
        self.progress_bar.set(0)
        self.fitness_label.configure(text="Best Fitness: N/A")
        self.update_idletasks()

        config = configparser.ConfigParser()
        config_path = os.path.join(project_root, 'config.ini')
        config.read(config_path)
        num_generations = config.getint('genetic_algorithm', 'num_generations', fallback=10)

        self.progress_queue = queue.Queue()
        self.ga_thread = threading.Thread(
            target=self._run_ga_in_thread,
            args=(all_cards, meta_decks, num_generations, self.progress_queue),
            daemon=True
        )
        self.ga_thread.start()
        self.after(100, self.check_ga_progress)

    def _run_ga_in_thread(self, all_cards, meta_decks, num_generations, q):
        try:
            results = run_ga(all_cards, meta_decks, num_generations=num_generations, progress_queue=q)
            q.put({"type": "finished", "result": results})
        except Exception as e:
            q.put({"type": "error", "message": str(e)})

    def check_ga_progress(self):
        try:
            message = self.progress_queue.get_nowait()
            msg_type = message.get("type")

            if msg_type == "progress":
                progress = message["current"] / message["total"]
                self.progress_bar.set(progress)
                self.fitness_label.configure(text=f"Best Fitness: {message['best_fitness']:.4f}")
                self.status_label.configure(text=f"Running... Generation {message['current']}/{message['total']}")
                self.after(100, self.check_ga_progress)
            elif msg_type == "status":
                self.status_label.configure(text=message["message"])
                self.after(100, self.check_ga_progress)
            elif msg_type == "finished":
                self.last_results = message["result"]
                self.status_label.configure(text="Optimization complete! Click 'View Results' to see the details.")
                self.progress_frame.grid_remove()
                self.run_button.configure(state="normal")
                self.view_results_button.grid()
            elif msg_type == "error":
                self.status_label.configure(text=f"Error: {message['message']}")
                self.progress_frame.grid_remove()
                self.run_button.configure(state="normal")
        except queue.Empty:
            if self.ga_thread.is_alive():
                self.after(100, self.check_ga_progress)
            else:
                self.status_label.configure(text="Optimizer finished unexpectedly.")
                self.progress_frame.grid_remove()
                self.run_button.configure(state="normal")

    def show_results_window(self):
        from collections import Counter
        if not self.last_results:
            return

        results_data = self.last_results['results']
        best_deck = self.last_results['best_deck']

        results_window = ctk.CTkToplevel(self)
        results_window.title("Optimizer Results")
        results_window.geometry("600x700")

        summary_frame = ctk.CTkFrame(results_window)
        summary_frame.pack(pady=10, padx=10, fill="x")
        summary_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(summary_frame, text="Final Fitness:", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", padx=5, pady=2)
        ctk.CTkLabel(summary_frame, text=f"{results_data['final_fitness']:.4f}").grid(row=0, column=1, sticky="w", padx=5, pady=2)

        ctk.CTkLabel(summary_frame, text="Raw Win Rate:", font=ctk.CTkFont(weight="bold")).grid(row=1, column=0, sticky="w", padx=5, pady=2)
        ctk.CTkLabel(summary_frame, text=f"{results_data['raw_win_rate']:.2%}").grid(row=1, column=1, sticky="w", padx=5, pady=2)

        ctk.CTkLabel(summary_frame, text="Consistency Score:", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, sticky="w", padx=5, pady=2)
        ctk.CTkLabel(summary_frame, text=f"{results_data['consistency_score']:.2%}").grid(row=2, column=1, sticky="w", padx=5, pady=2)

        win_rate_frame = ctk.CTkFrame(results_window)
        win_rate_frame.pack(pady=10, padx=10, fill="x")
        ctk.CTkLabel(win_rate_frame, text="Win Rates vs. Meta Decks", font=ctk.CTkFont(weight="bold")).pack(pady=5)

        for deck_name, rate in sorted(results_data['win_rates_by_meta_deck'].items()):
            deck_frame = ctk.CTkFrame(win_rate_frame, fg_color="transparent")
            deck_frame.pack(fill="x", padx=10)
            ctk.CTkLabel(deck_frame, text=f"{deck_name}:").pack(side="left")
            ctk.CTkLabel(deck_frame, text=f"{rate:.2%}").pack(side="right")

        decklist_frame = ctk.CTkFrame(results_window)
        decklist_frame.pack(pady=10, padx=10, fill="both", expand=True)
        ctk.CTkLabel(decklist_frame, text="Optimized Decklist", font=ctk.CTkFont(weight="bold")).pack()

        deck_text = ""
        card_counts = Counter(c.name for c in best_deck.cards)
        for name, count in sorted(card_counts.items()):
            deck_text += f"{count}x {name}\n"

        textbox = ctk.CTkTextbox(decklist_frame, height=300, width=400)
        textbox.pack(pady=10, padx=10, fill="both", expand=True)
        textbox.insert("0.0", deck_text)
        textbox.configure(state="disabled")

        results_window.transient(self)
        results_window.grab_set()

def main():
    """Main application loop."""
    app = MainApp()
    app.mainloop()

if __name__ == '__main__':
    main()
