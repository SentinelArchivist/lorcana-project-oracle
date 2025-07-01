import customtkinter as ctk
import os

from ..game_engine.card import Card
from ..game_engine.deck import Deck, load_meta_decks
from ..optimizer.runner import run_ga

# Get the project root for file path access, but don't modify sys.path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Project Oracle")
        self.geometry("500x250")

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        self.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(self, text="Project Oracle - Lorcana Deck Optimizer", font=ctk.CTkFont(size=20, weight="bold"))
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.welcome_label = ctk.CTkLabel(self, text="Welcome! Click 'Run Optimizer' to begin.", font=ctk.CTkFont(size=12))
        self.welcome_label.grid(row=1, column=0, padx=20, pady=10)

        self.status_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=10))
        self.status_label.grid(row=2, column=0, padx=20, pady=0)

        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.grid(row=3, column=0, padx=20, pady=20, sticky="s")

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
            return

        meta_decks = load_meta_decks(db_path, all_cards)
        if not meta_decks:
            self.status_label.configure(text="Error: Failed to load meta decks.")
            return

        self.status_label.configure(text="Running genetic algorithm...")
        self.update_idletasks()

        best_deck = run_ga(all_cards, meta_decks, num_generations=10)

        self.status_label.configure(text="Optimization complete!")
        self.display_results(best_deck)

    def display_results(self, best_deck):
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
