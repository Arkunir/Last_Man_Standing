import pickle
import random
import math

# Charger le modèle RL
with open("modele_ia_beauty_contest", "rb") as f:
    history_list = pickle.load(f)

# On prend le dernier Q-table de chaque IA
latest_q_tables = history_list[-1]

MULTIPLIERS = [0.5,0.6,0.7,0.8,0.9,1.1,1.2,1.3,1.4,1.5]
N_ACTIONS = 21
MAX_ROUNDS = 50

def discretize_choice(choice):
    return int(round(choice/5)*5)

class Player:
    def __init__(self, name, q_table=None):
        self.name = name
        self.lives = 10
        self.q_table = q_table
        self.last_choice = None
        self._was_elim = False

    def choose_action(self, state, banned=set(), epsilon=0):
        possible_actions = [i*5 for i in range(N_ACTIONS) if i*5 not in banned]
        if not possible_actions:
            possible_actions = [i*5 for i in range(N_ACTIONS)]
        if random.random() < epsilon or state not in self.q_table:
            choice = random.choice(possible_actions)
        else:
            q_vals = self.q_table[state]
            best_idx = max(possible_actions, key=lambda x: q_vals[x//5])
            choice = best_idx
        self.last_choice = choice
        return choice

    def get_state(self, multiplier, round_number, lives_list):
        mean_others = int(sum(lives_list)/len(lives_list)) if lives_list else 0
        mult_disc = int(multiplier*10)
        return (self.lives, mean_others, mult_disc, round_number)

# Créer les joueurs
human = Player("Vous")
ias = [Player(name, latest_q_tables[name]) for name in latest_q_tables.keys() if name != "Vous"]
players = [human] + ias

all_rules = [1,2,3,4,5,6]

# Jeu
multiplier = random.choice(MULTIPLIERS)
active_rules = []

for round_number in range(1, MAX_ROUNDS+1):
    alive_players = [p for p in players if p.lives>0]
    if len(alive_players) <= 1:
        break

    # Manche 5 : forcer une règle si aucune active
    if round_number == 5 and not active_rules and len(alive_players)>2:
        new_rule = random.choice(all_rules)
        active_rules.append(new_rule)

    # Règle 1 : multiplier change
    if 1 in active_rules:
        multiplier = random.choice(MULTIPLIERS)

    # Règle 6 : nombres interdits
    banned_numbers = set(random.sample(range(0,101),20)) if 6 in active_rules else set()
    print(f"\nManche {round_number} | Multiplicateur: {multiplier} | Nombres interdits: {sorted(list(banned_numbers))}")

    # Choix des joueurs
    choices = []
    state_dict = {}
    for p in alive_players:
        other_lives = [pl.lives for pl in alive_players if pl != p]
        state_dict[p] = p.get_state(multiplier, round_number, other_lives)
        if p == human:
            while True:
                try:
                    val = int(input(f"{p.name} (vies {p.lives}), entrez un nombre entre 0 et 100: "))
                    if val <0 or val>100 or val in banned_numbers:
                        raise ValueError
                    break
                except:
                    print("Valeur invalide ou interdite.")
            p.last_choice = val
        else:
            p.choose_action(state_dict[p], banned=banned_numbers)
        choices.append(p.last_choice)

    avg = sum(choices)/len(choices)
    target_real = avg * multiplier
    target = int(round(target_real))
    print(f"Choix: {[p.last_choice for p in alive_players]} | Moyenne x multiplicateur = {target_real:.2f} -> arrondi {target}")

    # Distances et gagnants
    distances = {p: abs(p.last_choice - target) for p in alive_players}
    min_dist = min(distances.values())
    winners = [p for p,d in distances.items() if d==min_dist]

    # Règle 2
    if 2 in active_rules and len(alive_players) > 2:
        max_dist = max(distances.values())
        far_players = [p for p,d in distances.items() if d==max_dist]
        winners = list(set(winners + far_players))

    # Règle 3
    exact_players = [p for p in alive_players if p.last_choice==target and 3 in active_rules]
    if exact_players:
        for p in alive_players:
            if p not in exact_players:
                p.lives -= 2
        winners = exact_players

    # Duel final si 2 joueurs
    if len(alive_players)==2:
        c1,c2 = alive_players[0].last_choice, alive_players[1].last_choice
        if {c1,c2}=={0,100}:
            if multiplier<1:
                winner = alive_players[0] if c1==100 else alive_players[1]
            else:
                winner = alive_players[0] if c1==0 else alive_players[1]
            loser = alive_players[0] if winner==alive_players[1] else alive_players[1]
            loser.lives -= 1
            winners = [winner]

    # Appliquer pertes
    for p in alive_players:
        if p not in winners:
            p.lives -= 1

    # Règle 5
    if 5 in active_rules:
        for p in players:
            if p.lives>0:
                p.lives = math.ceil(p.lives/2)

    # Nouvelles éliminations → ajouter règles
    newly_elim = [p for p in players if p.lives<=0 and not getattr(p,'_was_elim',False)]
    for p in newly_elim:
        p._was_elim = True
        print(f"{p.name} est éliminé !")
        if len([pl for pl in players if pl.lives>0]) > 2:
            remaining = [r for r in all_rules if r not in active_rules]
            if remaining:
                new_rule = random.choice(remaining)
                active_rules.append(new_rule)

    print("Vies après manche:", {p.name:p.lives for p in players})

# Fin de partie
alive_players = [p for p in players if p.lives>0]
if len(alive_players)==1:
    print(f"\n🎉 {alive_players[0].name} gagne la partie !")
elif len(alive_players)==0:
    print("\nAucun gagnant (égalité)")
else:
    print("\nFin de la partie avec plusieurs survivants:", [p.name for p in alive_players])
