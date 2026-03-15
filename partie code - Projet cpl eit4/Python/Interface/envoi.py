import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog  # <-- Ajout de filedialog
import random


class MenuEnvoiGUI:
    def __init__(self, parent, serial_conn=None):
        self.window = tk.Toplevel(parent)
        self.window.title("Menu d'Envoi")
        self.window.geometry("400x320")
        self.window.resizable(False, False)
        self.window.grab_set()

        self.ser = serial_conn

        style = ttk.Style()
        style.theme_use('default')
        style.configure("green.Horizontal.TProgressbar", background='green')

        self.total_bits = 1024
        self.bits_envoyes = 0
        self.type_actuel = ""
        self.donnees_a_envoyer = ""  # <-- Stockera le texte ou le chemin de l'image

        self.creer_frames()
        self.afficher_menu_choix()

    def creer_frames(self):
        # --- ECRAN 1 : CHOIX ---
        self.frame_choix = tk.Frame(self.window)
        tk.Label(self.frame_choix, text="Que souhaitez-vous envoyer ?", font=("Arial", 12, "bold")).pack(pady=20)

        grille_btn = tk.Frame(self.frame_choix)
        grille_btn.pack(pady=10)
        tk.Button(grille_btn, text="TXT", width=12, command=lambda: self.preparer_saisie("TXT")).grid(row=0, column=0,
                                                                                                      padx=10, pady=10)
        tk.Button(grille_btn, text="IMG", width=12, command=lambda: self.preparer_saisie("IMG")).grid(row=0, column=1,
                                                                                                      padx=10, pady=10)
        tk.Button(grille_btn, text="TXT_REQ", width=12, command=lambda: self.preparer_saisie("TXT_REQ")).grid(row=1,
                                                                                                              column=0,
                                                                                                              padx=10,
                                                                                                              pady=10)
        tk.Button(grille_btn, text="IMG_REQ", width=12, command=lambda: self.preparer_saisie("IMG_REQ")).grid(row=1,
                                                                                                              column=1,
                                                                                                              padx=10,
                                                                                                              pady=10)

        tk.Button(self.frame_choix, text="Annuler", command=self.window.destroy).pack(side=tk.BOTTOM, pady=10)

        # --- ECRAN 1.5 : SAISIE (NOUVEAU) ---
        self.frame_saisie = tk.Frame(self.window)
        # Le contenu de cet écran sera généré dynamiquement selon le choix (Texte ou Image)

        # --- ECRAN 2 : ENVOI EN COURS ---
        self.frame_envoi = tk.Frame(self.window)
        self.lbl_titre_envoi = tk.Label(self.frame_envoi, text="Envoi en cours...", font=("Arial", 12, "bold"))
        self.lbl_titre_envoi.pack(pady=30)
        self.progress_bar = ttk.Progressbar(self.frame_envoi, style="green.Horizontal.TProgressbar",
                                            orient="horizontal", length=300, mode="determinate")
        self.progress_bar.pack(pady=10)
        self.lbl_bits = tk.Label(self.frame_envoi, text="0 / 0 bits envoyés")
        self.lbl_bits.pack()

        # --- ECRAN 3 : RECEPTION ---
        self.frame_reception = tk.Frame(self.window)
        tk.Label(self.frame_reception, text="Réception de la réponse (Hex) :", font=("Arial", 10, "bold")).pack(pady=5)
        self.console_hex = scrolledtext.ScrolledText(self.frame_reception, width=45, height=12, bg="black",
                                                     fg="lightgreen", font=("Courier", 9))
        self.console_hex.pack(pady=5, padx=10)

    def cacher_tout(self):
        self.frame_choix.pack_forget()
        self.frame_saisie.pack_forget()
        self.frame_envoi.pack_forget()
        self.frame_reception.pack_forget()

    def afficher_menu_choix(self):
        self.cacher_tout()
        self.frame_choix.pack(expand=True, fill=tk.BOTH)

    # ==========================================
    # LOGIQUE DE SAISIE (NOUVEAU BLOC)
    # ==========================================
    def preparer_saisie(self, type_envoi):
        """Prépare l'écran de saisie en fonction du type de fichier"""
        self.type_actuel = type_envoi
        self.cacher_tout()

        # On vide l'écran de saisie précédent pour ne pas empiler les widgets
        for widget in self.frame_saisie.winfo_children():
            widget.destroy()

        tk.Label(self.frame_saisie, text=f"Préparation de l'envoi : {type_envoi}", font=("Arial", 12, "bold")).pack(
            pady=15)

        # Génération dynamique selon le choix
        if "TXT" in type_envoi:
            tk.Label(self.frame_saisie, text="Tapez votre message ci-dessous :").pack(pady=5)
            self.champ_texte = tk.Text(self.frame_saisie, height=5, width=40)
            self.champ_texte.pack(pady=5, padx=10)
        else:  # Si c'est une image
            tk.Label(self.frame_saisie, text="Sélectionnez l'image à envoyer :").pack(pady=5)

            frame_fichier = tk.Frame(self.frame_saisie)
            frame_fichier.pack(pady=10)

            self.champ_chemin = tk.Entry(frame_fichier, width=30, state="readonly")
            self.champ_chemin.pack(side=tk.LEFT, padx=5)

            tk.Button(frame_fichier, text="Parcourir...", command=self.choisir_fichier).pack(side=tk.LEFT)

        # Boutons de navigation
        frame_boutons = tk.Frame(self.frame_saisie)
        frame_boutons.pack(side=tk.BOTTOM, fill=tk.X, pady=15)

        tk.Button(frame_boutons, text="Retour", command=self.afficher_menu_choix).pack(side=tk.LEFT, padx=20)
        tk.Button(frame_boutons, text="Valider et Envoyer", bg="lightblue", command=self.valider_saisie).pack(
            side=tk.RIGHT, padx=20)

        self.frame_saisie.pack(expand=True, fill=tk.BOTH)

    def choisir_fichier(self):
        """Ouvre l'explorateur de fichiers pour choisir une image"""
        chemin_fichier = filedialog.askopenfilename(
            title="Choisir une image",
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp"), ("Tous les fichiers", "*.*")]
        )
        if chemin_fichier:
            # On débloque l'Entry temporairement pour y écrire le chemin
            self.champ_chemin.config(state="normal")
            self.champ_chemin.delete(0, tk.END)
            self.champ_chemin.insert(0, chemin_fichier)
            self.champ_chemin.config(state="readonly")

    def valider_saisie(self):
        """Vérifie que l'utilisateur a bien rempli le champ avant de lancer l'envoi"""
        if "TXT" in self.type_actuel:
            # .get("1.0", tk.END) permet de récupérer tout le contenu d'un widget tk.Text
            contenu = self.champ_texte.get("1.0", tk.END).strip()
            if not contenu:
                messagebox.showwarning("Attention", "Le message est vide !")
                return
            self.donnees_a_envoyer = contenu
        else:
            contenu = self.champ_chemin.get()
            if not contenu:
                messagebox.showwarning("Attention", "Aucune image sélectionnée !")
                return
            self.donnees_a_envoyer = contenu

        # Si tout est bon, on lance l'envoi
        print(f"Prêt à envoyer : {self.donnees_a_envoyer}")
        self.demarrer_envoi()

    # ==========================================
    # LOGIQUE D'ENVOI ET RÉCEPTION
    # ==========================================
    def demarrer_envoi(self):
        self.bits_envoyes = 0
        self.total_bits = 1024  # Valeur arbitraire de simulation

        self.cacher_tout()
        self.lbl_titre_envoi.config(text=f"Envoi en cours ({self.type_actuel})...")
        self.progress_bar["maximum"] = self.total_bits
        self.progress_bar["value"] = 0
        self.frame_envoi.pack(expand=True, fill=tk.BOTH)

        self.simuler_envoi_etape()

    def simuler_envoi_etape(self):
        if self.bits_envoyes < self.total_bits:
            self.bits_envoyes += 64
            if self.bits_envoyes > self.total_bits:
                self.bits_envoyes = self.total_bits

            self.progress_bar["value"] = self.bits_envoyes
            self.lbl_bits.config(text=f"{self.bits_envoyes} / {self.total_bits} bits envoyés")
            self.window.after(50, self.simuler_envoi_etape)
        else:
            self.fin_envoi()

    def fin_envoi(self):
        if "REQ" in self.type_actuel:
            self.demarrer_reception()
        else:
            messagebox.showinfo("Succès", "Envoi terminé avec succès.")
            self.window.destroy()

    def demarrer_reception(self):
        self.cacher_tout()
        self.console_hex.delete(1.0, tk.END)
        self.frame_reception.pack(expand=True, fill=tk.BOTH)

        self.octets_recus = 0
        self.octets_attendus = 32
        self.simuler_reception_etape()

    def simuler_reception_etape(self):
        if self.octets_recus < self.octets_attendus:
            octet_bidon = hex(random.randint(0, 255))[2:].zfill(2).upper()
            self.console_hex.insert(tk.END, f"{octet_bidon} ")
            self.console_hex.see(tk.END)
            self.octets_recus += 1
            self.window.after(random.randint(20, 100), self.simuler_reception_etape)
        else:
            self.fin_reception()

    def fin_reception(self):
        self.console_hex.insert(tk.END, "\n\n--- TERMINÉ ---")
        self.console_hex.see(tk.END)

        decodage_reussi = True
        if decodage_reussi:
            choix = messagebox.askyesno("Réception terminée",
                                        "Le fichier a été correctement décodé.\nVoulez-vous l'afficher maintenant ?")
            if choix:
                print(f"-> Affichage du résultat pour une requête {self.type_actuel}...")
        else:
            messagebox.showerror("Erreur", "Le fichier reçu est corrompu ou illisible.")

        self.window.destroy()


# BLOC DE TEST
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Application Principale")
    root.geometry("300x200")
    tk.Button(root, text="Ouvrir le Menu d'Envoi", command=lambda: MenuEnvoiGUI(root)).pack(expand=True)
    root.mainloop()