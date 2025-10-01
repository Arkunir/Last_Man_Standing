import tkinter as tk
from tkinter import messagebox
import random
import math

MULTIPLIERS = [0.5,0.6,0.7,0.8,0.9,1.1,1.2,1.3,1.4,1.5]
DEFAULT_ROUND_TIME = 20  # secondes par défaut

class Player:
    def __init__(self, name, lives):
        self.name = name
        self.lives = lives
        self.last_choice = None
        self._was_elim = False

class Game:
    def __init__(self, root):
        self.root = root
        self.root.title("Jeu multijoueur - hotseat")
        self.players = []
        self.round_time = DEFAULT_ROUND_TIME
        self.base_multiplier = random.choice(MULTIPLIERS)
        self.current_multiplier = self.base_multiplier
        self.active_rules = []
        self.all_rules = [1,2,3,4,5,6]  # uniquement 1..6
        self.banned_numbers = set()
        self.round_number = 0
        self.timer_id = None
        self.countdown = 0
        self.setup_start_screen()

    def setup_start_screen(self):
        for w in self.root.winfo_children():
            w.destroy()
        frame = tk.Frame(self.root, padx=10, pady=10)
        frame.pack()

        tk.Label(frame, text="Nombre de joueurs :").grid(row=0,column=0,sticky='w')
        self.n_players_var = tk.IntVar(value=2)
        tk.Spinbox(frame, from_=2, to=8, textvariable=self.n_players_var, width=5).grid(row=0,column=1,sticky='w')

        tk.Label(frame, text="Temps par manche (s) :").grid(row=1,column=0,sticky='w')
        self.time_var = tk.IntVar(value=DEFAULT_ROUND_TIME)
        tk.Entry(frame, textvariable=self.time_var, width=6).grid(row=1,column=1,sticky='w')

        tk.Label(frame, text=f"Multiplicateur initial (tiré aléatoirement) : {self.base_multiplier}").grid(row=2,column=0,columnspan=2,sticky='w',pady=(10,0))

        tk.Button(frame, text="Démarrer la partie", command=self.start_game).grid(row=4,column=0,columnspan=2,pady=(10,0))

    def start_game(self):
        n = self.n_players_var.get()
        if n < 2:
            messagebox.showerror("Erreur","Il faut au moins 2 joueurs")
            return
        self.players = []
        if n <= 3:
            lives = 10
        elif n >= 6:
            lives = 15
        else:
            lives = n*3-2
        for i in range(1, n+1):
            self.players.append(Player(f"Joueur {i}", lives))
        self.round_time = max(7, int(self.time_var.get()))
        self.current_multiplier = self.base_multiplier
        self.active_rules = []
        self.round_number = 0
        self.setup_game_screen()

    def setup_game_screen(self):
        for w in self.root.winfo_children():
            w.destroy()

        # Partie haute : infos
        self.top_frame = tk.Frame(self.root, padx=8, pady=8)
        self.top_frame.pack(fill='x')
        self.info_label = tk.Label(self.top_frame, text=self._game_info_text(), justify='left')
        self.info_label.pack(anchor='w')

        # Partie milieu gauche : entrées des joueurs
        self.mid_frame = tk.Frame(self.root, padx=8, pady=8)
        self.mid_frame.pack(side="left", fill="both", expand=True)
        self.entries = []
        self.entry_widgets = []
        for i, p in enumerate(self.players):
            row = tk.Frame(self.mid_frame)
            row.pack(fill='x', pady=2)
            lbl = tk.Label(row, text=f"{p.name} (vies: {p.lives})", width=18, anchor="w")
            lbl.pack(side='left')
            var = tk.StringVar()
            ent = tk.Entry(row, textvariable=var, width=6)
            ent.pack(side='left')
            self.entries.append(var)
            self.entry_widgets.append(ent)
            tk.Button(row, text="Auto", command=lambda v=var: v.set(str(random.randint(0,100)))).pack(side='left')

        # Partie milieu droite : nombres interdits
        self.right_frame = tk.Frame(self.root, padx=8, pady=8)
        self.right_frame.pack(side="right", fill="y")
        self.banned_label = tk.Label(self.right_frame, text="Nombres interdits :", font=("Arial",10,"bold"))
        self.banned_label.pack(anchor="n")
        self.banned_display = tk.Label(self.right_frame, text="", justify="left")
        self.banned_display.pack(anchor="n")

        # Partie basse : contrôles
        self.controls = tk.Frame(self.root, padx=8, pady=8)
        self.controls.pack(fill='x')
        self.countdown_label = tk.Label(self.controls, text=f"Temps restant: --")
        self.countdown_label.pack(side='left')
        tk.Button(self.controls, text="Soumettre maintenant", command=self.submit_choices).pack(side='right')
        self.round_button = tk.Button(self.controls, text="Démarrer manche", command=self.start_round)
        self.round_button.pack(side='right')

        # Zone de log
        self.log = tk.Text(self.root, height=12, state='disabled')
        self.log.pack(fill='both', padx=8, pady=8, expand=True)

        self.update_ui()

    def _game_info_text(self):
        rules_text = ', '.join(str(r) for r in sorted(self.active_rules)) if self.active_rules else 'Aucune'
        return f"Manche: {self.round_number} | Multiplicateur courant: {self.current_multiplier} | Règles actives: {rules_text}"

    def update_ui(self):
        for i, p in enumerate(self.players):
            row = self.mid_frame.winfo_children()[i]
            lbl = row.winfo_children()[0]
            lbl.config(text=f"{p.name} (vies: {p.lives})")
            if p.lives <= 0:
                self.entry_widgets[i].config(state="disabled")
            else:
                self.entry_widgets[i].config(state="normal")
        self.info_label.config(text=self._game_info_text())

        # Affichage des nombres interdits
        if 6 in self.active_rules and self.banned_numbers:
            cols = 5
            nums = sorted(self.banned_numbers)
            lines = []
            for i in range(0,len(nums),cols):
                lines.append(" ".join(f"{n:>2}" for n in nums[i:i+cols]))
            self.banned_display.config(text="\n".join(lines))
        else:
            self.banned_display.config(text="")

    def start_round(self):
        if self._alive_players_count() <= 1:
            self.end_game()
            return
        self.round_number += 1

        # Manche 5 : forcer une règle si aucune n'est active
        if self.round_number == 5 and not self.active_rules and self._alive_players_count() > 2:
            self.log_msg("Aucune règle active à la manche 5 → activation forcée d'une règle.")
            self._add_random_rule()

        # Règle 1 : changer multiplicateur chaque manche
        if 1 in self.active_rules:
            self.current_multiplier = random.choice(MULTIPLIERS)

        # Règle 4 : temps aléatoire
        if 4 in self.active_rules:
            self.countdown = random.randint(7,30)
        else:
            self.countdown = self.round_time

        # Règle 6 : nombres interdits
        if 6 in self.active_rules:
            self.banned_numbers = set(random.sample(range(0,101), 20))
        else:
            self.banned_numbers = set()

        for v in self.entries:
            v.set("")

        self.log_msg(f"--- Manche {self.round_number} démarrée (multiplier: {self.current_multiplier}, temps: {self.countdown}s) ---")
        self.update_ui()
        self.round_button.config(state='disabled')
        self._tick()

    def _tick(self):
        self.countdown_label.config(text=f"Temps restant: {self.countdown}s")
        if self.countdown <= 0:
            self.submit_choices()
            return
        self.countdown -= 1
        self.timer_id = self.root.after(1000, self._tick)

    def submit_choices(self):
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None

        choices = []
        for i, var in enumerate(self.entries):
            p = self.players[i]
            if p.lives <= 0:
                continue
            raw = var.get().strip()
            try:
                val = int(raw)
            except:
                val = None
            if val is None or val < 0 or val > 100 or val in self.banned_numbers:
                val = random.randint(0,100)
                self.log_msg(f"{p.name} n'a pas donné de choix valide; choix aléatoire {val} attribué")
            p.last_choice = val
            choices.append(val)

        if not choices:
            return
        avg = sum(choices)/len(choices)
        target_real = avg * self.current_multiplier
        target = int(round(target_real))
        self.log_msg(f"Choix: {choices}")
        self.log_msg(f"Moyenne: {avg:.2f} -> x {self.current_multiplier} = {target_real:.2f} arrondi => {target}")

        # Cas spécial duel final
        if self._alive_players_count() == 2:
            alive = [p for p in self.players if p.lives > 0]
            c1, c2 = alive[0].last_choice, alive[1].last_choice
            if self.current_multiplier < 1 and {c1,c2} == {0,100}:
                winner = alive[0] if c1 == 100 else alive[1]
                self.log_msg(f"Règle duel: {winner.name} gagne la manche (100 vs 0 avec multiplicateur <1)")
                loser = alive[0] if winner==alive[1] else alive[1]
                loser.lives -= 1
                self._post_round_cleanup()
                return
            elif self.current_multiplier > 1 and {c1,c2} == {0,100}:
                winner = alive[0] if c1 == 0 else alive[1]
                self.log_msg(f"Règle duel: {winner.name} gagne la manche (0 vs 100 avec multiplicateur >1)")
                loser = alive[0] if winner==alive[1] else alive[1]
                loser.lives -= 1
                self._post_round_cleanup()
                return

        # Règle 3 : exact
        exact_players = [p for p in self.players if p.last_choice == target and p.lives>0]
        if exact_players and 3 in self.active_rules:
            self.log_msg(f"Exact trouvé par: {', '.join(p.name for p in exact_players)} -> ces joueurs ne perdent pas, les autres perdent 2 vies")
            for p in self.players:
                if p.lives > 0 and p not in exact_players:
                    p.lives -= 2
            self._post_round_cleanup()
            return

        # distances
        alive_players = [p for p in self.players if p.lives>0]
        distances = {p: abs(p.last_choice - target) for p in alive_players}
        if not distances:
            self.end_game()
            return
        min_dist = min(distances.values())
        winners = [p for p,d in distances.items() if d==min_dist]

        if 2 in self.active_rules and self._alive_players_count() > 2:
            max_dist = max(distances.values())
            far_players = [p for p,d in distances.items() if d==max_dist]
            winners = list(set(winners + far_players))

        self.log_msg(f"Joueur(s) les plus proches: {', '.join(p.name for p in winners)}")
        for p in alive_players:
            if p not in winners:
                p.lives -= 1

        if 5 in self.active_rules:
            self.log_msg("Règle 5 active: division des vies par 2 (arrondi supérieur)")
            for p in self.players:
                if p.lives > 0:
                    p.lives = math.ceil(p.lives / 2)

        self._post_round_cleanup()

    def _post_round_cleanup(self):
        for p in self.players:
            self.log_msg(f"{p.name} -> vies: {p.lives}")
        # plus d'ajout de règle si seulement 2 joueurs vivants
        if self._alive_players_count() > 2:
            newly_eliminated = [p for p in self.players if p.lives <= 0 and not p._was_elim]
            for p in newly_eliminated:
                p._was_elim = True
                self.log_msg(f"{p.name} est éliminé ! Une nouvelle règle va être ajoutée.")
                self._add_random_rule()
        self.round_button.config(state='normal')
        self.update_ui()
        if self._alive_players_count() <= 1:
            self.end_game()

    def _add_random_rule(self):
        remaining = [r for r in self.all_rules if r not in self.active_rules]
        if not remaining:
            self.log_msg("Toutes les règles sont déjà actives.")
            return
        new = random.choice(remaining)
        self.active_rules.append(new)
        self.log_msg(f"Nouvelle règle activée: {new} -> {self._rule_text(new)}")
        if new == 5:
            for p in self.players:
                if p.lives > 0:
                    p.lives = math.ceil(p.lives / 2)
            self.log_msg("Application immédiate de la règle 5: vies divisées par 2")
        if new == 1:
            self.current_multiplier = random.choice(MULTIPLIERS)
            self.log_msg(f"Multiplicateur changé maintenant: {self.current_multiplier}")
        self.update_ui()

    def _rule_text(self, r):
        texts = {
            1: "La valeur multiplicative change chaque round",
            2: "Les joueurs les plus éloignés sont aussi protégés (sauf si seulement 2 joueurs restants)",
            3: "Si un joueur obtient la valeur exacte, les autres perdent 2 vies",
            4: "Le temps de réflexion devient aléatoire entre 7 et 30s",
            5: "Les vies de tous les joueurs sont divisées par 2 (arrondi supérieur)",
            6: "20 nombres aléatoires (0..100) sont interdits chaque round"
        }
        return texts.get(r, '')

    def _alive_players_count(self):
        return sum(1 for p in self.players if p.lives > 0)

    def log_msg(self, msg):
        self.log.config(state='normal')
        self.log.insert('end', msg + '\n')
        self.log.see('end')
        self.log.config(state='disabled')

    def end_game(self):
        winners = [p for p in self.players if p.lives > 0]
        if not winners:
            self.log_msg("Fin de la partie: aucun gagnant (égalité) !")
            messagebox.showinfo("Fin","Aucun gagnant — égalité")
        elif len(winners) == 1:
            self.log_msg(f"Fin de la partie: {winners[0].name} gagne !")
            messagebox.showinfo("Fin", f"{winners[0].name} gagne !")
        else:
            self.log_msg(f"Fin de la partie: plusieurs gagnants: {', '.join(p.name for p in winners)}")
            messagebox.showinfo("Fin", f"Gagnants: {', '.join(p.name for p in winners)}")
        if messagebox.askyesno("Rejouer?","Voulez-vous lancer une nouvelle partie ?"):
            self.base_multiplier = random.choice(MULTIPLIERS)
            self.setup_start_screen()
        else:
            self.root.quit()

if __name__ == '__main__':
    root = tk.Tk()
    game = Game(root)
    root.mainloop()
