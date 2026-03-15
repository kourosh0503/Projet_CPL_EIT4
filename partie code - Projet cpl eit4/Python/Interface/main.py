import tkinter as tk
from tkinter import messagebox
import time


class ParametresGUI:
    def __init__(self, root, serial_conn=None, logger_func=print):
        # Création de la fenêtre secondaire
        self.window = tk.Toplevel(root)
        self.window.title("Menu Paramètres")
        self.window.geometry("500x150")
        self.window.resizable(True, True)

        # Rend la fenêtre modale (bloque l'accès à la fenêtre principale tant qu'elle est ouverte)
        self.window.grab_set()

        # Récupération de la connexion série et de la fonction de log du parent
        self.ser = serial_conn
        self.log = logger_func

        self.creer_widgets()

    def creer_widgets(self):
        # --- 1) Barre glissante (Slider) pour le Treshold ---
        frame_treshold = tk.Frame(self.window)
        frame_treshold.pack(pady=15, fill=tk.X, padx=20)

        tk.Label(frame_treshold, text="Seuil DAC [cV] (0-330) :").pack(side=tk.TOP, anchor='w')
        self.slider_treshold = tk.Scale(frame_treshold, from_=0, to=330, orient=tk.HORIZONTAL, length=300)
        self.slider_treshold.pack(side=tk.TOP)

        # --- 2) Zone de texte pour la vitesse ---
        frame_speed = tk.Frame(self.window)
        frame_speed.pack(pady=10, fill=tk.X, padx=20)

        tk.Label(frame_speed, text="Vitesse [B/s] (ex: 503 -> 50*10^3) :").pack(side=tk.LEFT)
        self.entry_speed = tk.Entry(frame_speed, width=10)
        self.entry_speed.pack(side=tk.LEFT, padx=10)

        tk.Button(frame_speed, text="Appliquer", command=self.appliquer_parametres).pack(side=tk.RIGHT)

        # --- 3) Bouton Test + Point d'état ---
        frame_test = tk.Frame(self.window)
        frame_test.pack(pady=20, fill=tk.X, padx=20)

        self.btn_test = tk.Button(frame_test, text="Tester la connexion", command=self.executer_test)
        self.btn_test.pack(side=tk.LEFT)

        self.canvas_status = tk.Canvas(frame_test, width=20, height=20, highlightthickness=0)
        self.canvas_status.pack(side=tk.LEFT, padx=10)

        # Point gris par défaut
        self.voyant_status = self.canvas_status.create_oval(2, 2, 18, 18, fill="gray", outline="darkgray")

    def appliquer_parametres(self):
        """Envoie les paramètres de vitesse et de seuil à l'Arduino"""
        val_treshold = int(self.slider_treshold.get())
        val_speed = self.entry_speed.get().strip()

        # Vérification si la connexion existe et est ouverte
        if self.ser is None or not hasattr(self.ser, 'is_open') or not self.ser.is_open:
            messagebox.showerror("Erreur", "Non connecté à l'Arduino.")
            return

        try:
            # Envoi du seuil (Treshold)
            cmd_treshold = f"t{val_treshold:03d}"
            self.ser.write(cmd_treshold.encode(encoding='ascii', errors='ignore'))
            self.log(f"Paramètre Seuil envoyé : {cmd_treshold}")

            time.sleep(0.1)  # Petite pause pour laisser l'Arduino traiter la commande

            # Envoi de la vitesse (Speed)
            if val_speed.isdigit() and len(val_speed) == 3:
                cmd_speed = f"s{val_speed}"
                self.ser.write(cmd_speed.encode(encoding='ascii', errors='ignore'))
                self.log(f"Paramètre Vitesse envoyé : {cmd_speed}")
            elif val_speed:
                messagebox.showwarning("Format invalide", "La vitesse doit être un code à 3 chiffres (ex: 503).")

        except Exception as e:
            self.log(f"Erreur lors de l'envoi des paramètres : {e}")

    def executer_test(self):
        """Vrai test de communication série (Ping)"""
        self.log("Exécution du test de connexion...")
        succes_connexion = False

        if self.ser is not None and hasattr(self.ser, 'is_open') and self.ser.is_open:
            try:
                # Nettoie le buffer entrant avant le test
                self.ser.reset_input_buffer()
                self.ser.write('test'.encode(encoding='ascii', errors='ignore'))

                # Attente de la réponse
                reponse = self.ser.readline().decode(encoding='ascii', errors='ignore').strip()

                if reponse:
                    succes_connexion = True
                    self.log(f"Test réussi. Réponse de l'Arduino : {reponse}")

            except Exception as e:
                self.log(f"Erreur de communication : {e}")
        else:
            self.log("Impossible de tester : port série fermé ou inexistant.")

        # --- Mise à jour visuelle du voyant ---
        if succes_connexion:
            self.canvas_status.itemconfig(self.voyant_status, fill="#00FF00")  # Vert
        else:
            self.canvas_status.itemconfig(self.voyant_status, fill="red")  # Rouge


# ==========================================
# BLOC DE TEST INDÉPENDANT
# ==========================================
if __name__ == "__main__":
    # Ce bloc ne s'exécute que si tu lances ce fichier directement
    root = tk.Tk()
    root.title("Fenêtre Principale Factice")
    root.geometry("400x300")

    # Bouton de test pour ouvrir le menu (sans vraie connexion série)
    tk.Button(
        root,
        text="Ouvrir les paramètres",
        command=lambda: ParametresGUI(root, serial_conn=None)
    ).pack(expand=True)

    root.mainloop()