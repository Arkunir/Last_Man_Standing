import tkinter as tk
from tkinter import messagebox
import random
import math
import pickle
import numpy as np

MULTIPLIERS = [0.5,0.6,0.7,0.8,0.9,1.1,1.2,1.3,1.4,1.5]
DEFAULT_ROUND_TIME = 20
N_ACTIONS = 21  # pour les IA

# Charger le modèle RL
with open("modele_ia_beauty_contest", "rb") as f:
    history_list = pickle.load(f)
latest_q_tables = history_list[-1]  # dernier épisode

def discretize_choice(choice):
    return int(round(choice/5)*5)

class Player:
    def __init__(self, name, lives, q_table=None):
        self.name = name
        self.lives = lives
        self.q_table = q_table
        self.last_choice = None
        self._was_elim = False

    def get_state(self, multiplier, round_number, lives_list):
        mean_others = int(sum(lives_list)/len(lives_list)) if lives_list else 0
        mult_disc = int(multiplier*10)
        return (self.lives, mean_others, mult_disc, round_number)

    def choose_ai_action(self, state, banned=set(), epsilon=0):
        if not self.q_table or random.random() < epsilon or state not in self.q_table:
            choice = random.choice([i*5 for i in range(N_ACTIONS) if i*5 not in banned] or [i*5 for i in range(N_ACTIONS)])
        else:
            q_vals = self.q_table[state]
            possible = [i*5 for i in range(N_ACTIONS) if i*5 not in banned]
            if not possible: possible = [i*5 for i in range(N_ACTIONS)]
            choice = max(possible, key=lambda x: q_vals[x//5])
        self.last_choice = choice
        return choice

class Game:
    def __init__(self, root):
        self.root = root
        self.root.title("Beauty Contest - Humain vs IA")
        self.players = []
        self.round_time = DEFAULT_ROUND_TIME
        self.base_multiplier = random.choice(MULTIPLIERS)
        self.current_multiplier = self.base_multiplier
        self.active_rules = []
        self.all_rules = [1,2,3,4,5,6]
        self.banned_numbers = set()
        self.round_number = 0
        self.timer_id = None
        self.countdown = 0
        self.setup_start_screen()

    def setup_start_screen(self):
        for w in self.root.winfo_children(): w.destroy()
        frame = tk.Frame(self.root,padx=10,pady=10); frame.pack()
        tk.Label(frame,text="Temps par manche (s) :").grid(row=0,column=0,sticky='w')
        self.time_var = tk.IntVar(value=DEFAULT_ROUND_TIME)
        tk.Entry(frame,textvariable=self.time_var,width=6).grid(row=0,column=1,sticky='w')
        tk.Button(frame,text="Démarrer la partie",command=self.start_game).grid(row=1,column=0,columnspan=2,pady=(10,0))

    def start_game(self):
        lives = 10
        human = Player("Vous", lives)
        # Ajouter 4 IA avec Q-table
        ia_players = [Player(name, lives, latest_q_tables[name]) for name in latest_q_tables.keys() if name != "Vous"]
        self.players = [human]+ia_players[:4]
        self.round_time = max(7,int(self.time_var.get()))
        self.current_multiplier = self.base_multiplier
        self.active_rules = []
        self.round_number = 0
        self.setup_game_screen()

    def setup_game_screen(self):
        for w in self.root.winfo_children(): w.destroy()
        self.top_frame = tk.Frame(self.root,padx=8,pady=8); self.top_frame.pack(fill='x')
        self.info_label = tk.Label(self.top_frame,text=self._game_info_text(),justify='left'); self.info_label.pack(anchor='w')

        self.mid_frame = tk.Frame(self.root,padx=8,pady=8); self.mid_frame.pack(side="left",fill="both",expand=True)
        self.entries = []; self.entry_widgets = []
        for i,p in enumerate(self.players):
            row = tk.Frame(self.mid_frame); row.pack(fill='x',pady=2)
            lbl = tk.Label(row,text=f"{p.name} (vies: {p.lives})",width=18,anchor="w"); lbl.pack(side='left')
            var = tk.StringVar(); ent = tk.Entry(row,textvariable=var,width=6); ent.pack(side='left')
            self.entries.append(var); self.entry_widgets.append(ent)
            if p.q_table: ent.config(state="disabled")  # IA ne modifie pas
            tk.Button(row,text="Auto",command=lambda v=var: v.set(str(random.randint(0,100)))).pack(side='left')

        self.right_frame = tk.Frame(self.root,padx=8,pady=8); self.right_frame.pack(side="right",fill="y")
        self.banned_label = tk.Label(self.right_frame,text="Nombres interdits :",font=("Arial",10,"bold")); self.banned_label.pack(anchor="n")
        self.banned_display = tk.Label(self.right_frame,text="",justify="left"); self.banned_display.pack(anchor="n")

        self.controls = tk.Frame(self.root,padx=8,pady=8); self.controls.pack(fill='x')
        self.countdown_label = tk.Label(self.controls,text=f"Temps restant: --"); self.countdown_label.pack(side='left')
        tk.Button(self.controls,text="Soumettre maintenant",command=self.submit_choices).pack(side='right')
        self.round_button = tk.Button(self.controls,text="Démarrer manche",command=self.start_round); self.round_button.pack(side='right')

        self.log = tk.Text(self.root,height=12,state='disabled'); self.log.pack(fill='both',padx=8,pady=8,expand=True)
        self.update_ui()

    def _game_info_text(self):
        rules_text = ', '.join(str(r) for r in sorted(self.active_rules)) if self.active_rules else 'Aucune'
        return f"Manche: {self.round_number} | Multiplicateur: {self.current_multiplier} | Règles actives: {rules_text}"

    def update_ui(self):
        for i,p in enumerate(self.players):
            row = self.mid_frame.winfo_children()[i]; lbl = row.winfo_children()[0]
            lbl.config(text=f"{p.name} (vies: {p.lives})")
            self.entry_widgets[i].config(state="normal" if p.lives>0 and not p.q_table else "disabled")
        self.info_label.config(text=self._game_info_text())
        if 6 in self.active_rules and self.banned_numbers:
            nums = sorted(self.banned_numbers); lines=[]
            for i in range(0,len(nums),5): lines.append(" ".join(f"{n:>2}" for n in nums[i:i+5]))
            self.banned_display.config(text="\n".join(lines))
        else: self.banned_display.config(text="")

    def start_round(self):
        if self._alive_players_count()<=1: self.end_game(); return
        self.round_number+=1
        if self.round_number==5 and not self.active_rules and self._alive_players_count()>2:
            self.log_msg("Activation forcée d'une règle à la manche 5")
            self._add_random_rule()
        if 1 in self.active_rules: self.current_multiplier=random.choice(MULTIPLIERS)
        self.countdown = random.randint(7,30) if 4 in self.active_rules else self.round_time
        self.banned_numbers = set(random.sample(range(0,101),20)) if 6 in self.active_rules else set()
        for v in self.entries: v.set("")
        self.log_msg(f"--- Manche {self.round_number} démarrée (multiplier: {self.current_multiplier}, temps: {self.countdown}s) ---")
        self.update_ui(); self.round_button.config(state='disabled'); self._tick()

    def _tick(self):
        self.countdown_label.config(text=f"Temps restant: {self.countdown}s")
        if self.countdown<=0: self.submit_choices(); return
        self.countdown-=1; self.timer_id=self.root.after(1000,self._tick)

    def submit_choices(self):
        if self.timer_id: self.root.after_cancel(self.timer_id); self.timer_id=None
        choices=[]
        for i,var in enumerate(self.entries):
            p=self.players[i]
            if p.lives<=0: continue
            if p.q_table:
                alive=[pl for pl in self.players if pl.lives>0 and pl!=p]
                state=p.get_state(self.current_multiplier,self.round_number,[pl.lives for pl in alive])
                p.choose_ai_action(state,self.banned_numbers)
            else:
                try: val=int(var.get().strip())
                except: val=None
                if val is None or val<0 or val>100 or val in self.banned_numbers:
                    val=random.randint(0,100)
                    self.log_msg(f"{p.name} choix invalide → {val} attribué")
                p.last_choice=val
            choices.append(p.last_choice)

        avg=sum(choices)/len(choices)
        target_real=avg*self.current_multiplier
        target=int(round(target_real))
        self.log_msg(f"Choix: {choices} | Moyenne x multiplicateur = {target_real:.2f} -> arrondi {target}")
        # distances et gagnants
        alive_players=[p for p in self.players if p.lives>0]
        distances={p:abs(p.last_choice-target) for p in alive_players}
        min_dist=min(distances.values()); winners=[p for p,d in distances.items() if d==min_dist]
        if 2 in self.active_rules and self._alive_players_count()>2:
            max_dist=max(distances.values()); far_players=[p for p,d in distances.items() if d==max_dist]; winners=list(set(winners+far_players))
        for p in alive_players:
            if p not in winners: p.lives-=1
        self._post_round_cleanup()

    def _post_round_cleanup(self):
        for p in self.players: self.log_msg(f"{p.name} -> vies: {p.lives}")
        if self._alive_players_count()>2:
            newly_elim=[p for p in self.players if p.lives<=0 and not p._was_elim]
            for p in newly_elim: p._was_elim=True; self.log_msg(f"{p.name} éliminé"); self._add_random_rule()
        self.round_button.config(state='normal'); self.update_ui()
        if self._alive_players_count()<=1: self.end_game()

    def _add_random_rule(self):
        remaining=[r for r in self.all_rules if r not in self.active_rules]
        if not remaining: return
        new=random.choice(remaining); self.active_rules.append(new)
        self.log_msg(f"Nouvelle règle activée: {new}")
        if new==5: 
            for p in self.players:
                if p.lives>0: p.lives=math.ceil(p.lives/2)
            self.log_msg("Application immédiate de la règle 5: vies divisées par 2")
        if new==1: self.current_multiplier=random.choice(MULTIPLIERS)
        self.update_ui()

    def _alive_players_count(self): return sum(1 for p in self.players if p.lives>0)
    def log_msg(self,msg): self.log.config(state='normal'); self.log.insert('end',msg+'\n'); self.log.see('end'); self.log.config(state='disabled')

    def end_game(self):
        winners=[p for p in self.players if p.lives>0]
        if not winners: msg="Aucun gagnant (égalité)"
        elif len(winners)==1: msg=f"{winners[0].name} gagne !"
        else: msg=f"Gagnants: {', '.join(p.name for p in winners)}"
        self.log_msg(msg); messagebox.showinfo("Fin",msg)
        if messagebox.askyesno("Rejouer?","Voulez-vous lancer une nouvelle partie ?"): self.base_multiplier=random.choice(MULTIPLIERS); self.setup_start_screen()
        else: self.root.quit()

if __name__=='__main__':
    root=tk.Tk()
    game=Game(root)
    root.mainloop()
