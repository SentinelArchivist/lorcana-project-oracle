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

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(self, text="Project Oracle - Lorcana Deck Optimizer", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10), columnspan=1)

        self.welcome_label = ctk.CTkLabel(self, text="Welcome! Click 'Run Optimizer' to begin.", font=ctk.CTkFont(size=12))
        self.welcome_label.grid(row=1, column=0, padx=20, pady=10)

        self.status_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=10))
        self.status_label.grid(row=2, column=0, padx=20, pady=0)

        # --- Progress Bar and Fitness Label ---
        self.progress_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.progress_frame.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(side="left", expand=True, fill="x", padx=(0, 10))
        self.progress_bar.set(0)

        self.fitness_label = ctk.CTkLabel(self.progress_frame, text="Best Fitness: N/A", font=ctk.CTkFont(size=12))
        self.fitness_label.pack(side="left")
        self.progress_frame.grid_remove() # Hide it initially

        # --- Buttons ---
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.grid(row=4, column=0, padx=20, pady=20, sticky="s")

        self.run_button = ctk.CTkButton(self.button_frame, text="Run Optimizer", command=self.run_optimizer)
        self.run_button.grid(row=0, column=0, padx=10)

        self.exit_button = ctk.CTkButton(self.button_frame, text="Exit", command=self.destroy)
        self.exit_button.grid(row=0, column=1, padx=10)

    def run_optimizer(self):
        self.run_button.configure(state="disabled")
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
        """Wrapper to run GA and put the final result in the queue."""
        try:
            best_deck = run_ga(all_cards, meta_decks, num_generations=num_generations, progress_queue=q)
            q.put({"type": "complete", "result": best_deck})
        except Exception as e:
            q.put({"type": "error", "message": str(e)})

    def check_ga_progress(self):
        """Periodically check the queue for updates from the GA thread."""
        try:
            message = self.progress_queue.get_nowait()
            if message["type"] == "progress":
                progress = message["current"] / message["total"]
                self.progress_bar.set(progress)
                self.fitness_label.configure(text=f"Best Fitness: {message['best_fitness']:.4f}")
                self.status_label.configure(text=f"Running... Generation {message['current']}/{message['total']}")
                self.after(100, self.check_ga_progress)
            elif message["type"] == "complete":
                self.status_label.configure(text="Optimization complete!")
                self.progress_frame.grid_remove()
                self.run_button.configure(state="normal")
                self.display_results(message["result"])
            elif message["type"] == "error":
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

    def display_results(self, best_deck):
        if not best_deck:
            self.status_label.configure(text="Optimization failed to find a valid deck.")
            return

        results_window = ctk.CTkToplevel(self)
        results_window.title("Optimizer Results")
        results_window.geometry("400x500")

        title_label = ctk.CTkLabel(results_window, text=f"Best Deck Found: {best_deck.name}", font=ctk.CTkFont(size=16, weight="bold"))
        title_label.pack(pady=10)

        results_textbox = ctk.CTkTextbox(results_window, width=380, height=400, font=ctk.CTkFont(family="monospace"))
        results_textbox.pack(pady=10, padx=10, fill="both", expand=True)

        card_counts = {}
        for card in best_deck.cards:
            card_counts[card.name] = card_counts.get(card.name, 0) + 1
        
        results_text = ""
        for card_name, count in sorted(card_counts.items()):
            results_text += f"{count}x {card_name}\n"
        
        results_textbox.insert("0.0", results_text)
        results_textbox.configure(state="disabled")

def main():
    """Main application loop."""
    app = MainApp()
    app.mainloop()

if __name__ == '__main__':
    main()
