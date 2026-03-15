import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import time
import threading
import sys
import cv2
import numpy as np

# Import des fonctions de ton module Arduino
from trans_arduino import *

# Variables globales script d'origine
im = ''
txt = ''
data_cont = ''


# ==========================================
# 0. FENÊTRE PRINCIPALE
# ==========================================
class ApplicationPrincipale:
    def __init__(self, root):
        self.root = root
        self.root.title("Interface PC - Arduino")
        self.root.geometry("450x300")
        self.ser = None
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.creer_widgets()

    def creer_widgets(self):
        frame_conn = tk.Frame(self.root)
        frame_conn.pack(pady=15)

        tk.Label(frame_conn, text="Port COM :").pack(side=tk.LEFT)

        self.combo_port = ttk.Combobox(frame_conn, width=15, state="readonly")
        self.combo_port.pack(side=tk.LEFT, padx=5)
        self.actualiser_ports()

        btn_actualiser = tk.Button(frame_conn, text="↻", command=self.actualiser_ports)
        btn_actualiser.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_conn = tk.Button(frame_conn, text="Connecter", command=self.connecter_serie)
        self.btn_conn.pack(side=tk.LEFT)

        frame_menu = tk.Frame(self.root)
        frame_menu.pack(expand=True)

        tk.Button(frame_menu, text="1. Paramètres", width=20, height=2, command=self.ouvrir_parametres).pack(pady=10)
        tk.Button(frame_menu, text="2. Envoi", width=20, height=2, command=self.ouvrir_envoi).pack(pady=10)

    def actualiser_ports(self):
        ports_dispos = [prt.device for prt in ports_list()]
        self.combo_port['values'] = ports_dispos
        if ports_dispos:
            self.combo_port.current(0)
        else:
            self.combo_port.set("")

    def connecter_serie(self):
        port = self.combo_port.get().strip()
        if not port:
            messagebox.showwarning("Erreur", "Veuillez sélectionner un port COM.")
            return

        try:
            self.ser = open_connexion(port, baudrate=115200, timeout=1)
            self.ser.readline()
            messagebox.showinfo("Succès", f"Connecté au port {port}")
            self.btn_conn.config(text="Connecté", bg="lightgreen", state="disabled")
            self.combo_port.config(state="disabled")
        except Exception as e:
            messagebox.showerror("Erreur de connexion", f"Impossible d'ouvrir le port {port}.\n\n{e}")

    def ouvrir_parametres(self):
        MenuParametres(self.root, self.ser)

    def ouvrir_envoi(self):
        MenuEnvoi(self.root, self.ser)

    def on_closing(self):
        if self.ser and self.ser.is_open:
            close_connexion(self.ser)
        self.root.destroy()


# ==========================================
# 1. MENU PARAMÈTRES
# ==========================================
class MenuParametres:
    def __init__(self, parent, serial_conn):
        self.fenetre = tk.Toplevel(parent)
        self.fenetre.title("Menu Paramètres")
        self.fenetre.geometry("350x300")
        self.fenetre.grab_set()

        self.ser = serial_conn
        self.creer_widgets()

    def creer_widgets(self):
        frame_treshold = tk.Frame(self.fenetre)
        frame_treshold.pack(pady=15, fill=tk.X, padx=20)
        tk.Label(frame_treshold, text="Seuil DAC [cV] (0-330):").pack(anchor='w')
        self.slider_treshold = tk.Scale(frame_treshold, from_=0, to=330, orient=tk.HORIZONTAL, length=300)
        self.slider_treshold.pack()

        frame_test = tk.Frame(self.fenetre)
        frame_test.pack(pady=15, fill=tk.X, padx=20)
        btn_test = tk.Button(frame_test, text="Test Arduino", command=self.tester_connexion)
        btn_test.pack(side=tk.LEFT)
        self.canvas_dot = tk.Canvas(frame_test, width=20, height=20, highlightthickness=0)
        self.canvas_dot.pack(side=tk.LEFT, padx=10)
        self.dot = self.canvas_dot.create_oval(2, 2, 18, 18, fill="gray", outline="darkgray")

        frame_vitesse = tk.Frame(self.fenetre)
        frame_vitesse.pack(pady=15, fill=tk.X, padx=20)
        tk.Label(frame_vitesse, text="Vitesse [B/s] (ex: 503) :").pack(side=tk.LEFT)
        self.entry_speed = tk.Entry(frame_vitesse, width=10)
        self.entry_speed.pack(side=tk.LEFT, padx=10)

        tk.Button(self.fenetre, text="Appliquer les réglages", bg="lightblue", command=self.appliquer_reglages).pack(
            pady=10)

    def tester_connexion(self):
        if not self.ser or not self.ser.is_open:
            messagebox.showerror("Erreur", "Le port série n'est pas connecté.")
            self.canvas_dot.itemconfig(self.dot, fill="red")
            return
        try:
            self.ser.reset_input_buffer()
            self.ser.write('test'.encode('ascii', 'ignore'))
            reponse = self.ser.readline().decode('ascii', 'ignore').strip()

            if reponse:
                self.canvas_dot.itemconfig(self.dot, fill="#00FF00")
            else:
                self.canvas_dot.itemconfig(self.dot, fill="red")
        except Exception as e:
            self.canvas_dot.itemconfig(self.dot, fill="red")
            messagebox.showerror("Erreur", str(e))

    def appliquer_reglages(self):
        if not self.ser or not self.ser.is_open:
            messagebox.showerror("Erreur", "Non connecté.")
            return

        val_treshold = int(self.slider_treshold.get())
        val_speed = self.entry_speed.get().strip()

        try:
            self.ser.reset_input_buffer()

            # --- 1. Envoi et lecture du Seuil (Treshold) ---
            self.ser.write(f"t{val_treshold:03d}".encode('ascii'))

            # On lit jusqu'au saut de ligne renvoyé par l'Arduino
            rep_treshold = self.ser.readline().decode('ascii', 'ignore').strip()
            if not rep_treshold:
                rep_treshold = "Aucune réponse"

            message_reponse = f"Réponse Seuil : {rep_treshold}"

            # --- 2. Envoi et lecture de la Vitesse (si renseignée) ---
            if val_speed:
                if len(val_speed) == 3 and val_speed.isdigit() and int(val_speed[2]) <= 3:
                    self.ser.write(f"s{val_speed}".encode('ascii'))

                    # On fait un deuxième readline() pour attendre la réponse de la vitesse
                    rep_speed = self.ser.readline().decode('ascii', 'ignore').strip()
                    if not rep_speed:
                        rep_speed = "Aucune réponse"

                    message_reponse += f"\nRéponse Vitesse : {rep_speed}"

                    messagebox.showinfo("Succès", f"Réglages appliqués.\n\n{message_reponse}")
                else:
                    messagebox.showwarning("Format invalide", "Vitesse = 3 chiffres, exposant <= 3.")
            else:
                messagebox.showinfo("Succès", f"Seuil appliqué (Vitesse ignorée).\n\n{message_reponse}")

        except Exception as e:
            messagebox.showerror("Erreur", str(e))


# ==========================================
# 2. MENU ENVOI ET RÉCEPTION
# ==========================================
class MenuEnvoi:
    def __init__(self, parent, serial_conn):
        self.fenetre = tk.Toplevel(parent)
        self.fenetre.title("Menu Envoi")
        self.fenetre.geometry("450x450")
        self.fenetre.grab_set()

        self.ser = serial_conn
        self.type_actuel = ""
        self.donnees_a_envoyer = ""
        self.hex_limit_atteinte = False

        # --- Variables pour la preview en direct ---
        self.live_preview_active = False
        self.current_data_lock = threading.Lock()
        self.current_data_snapshot = bytearray()
        # -------------------------------------------

        style = ttk.Style()
        style.theme_use('default')
        style.configure("green.Horizontal.TProgressbar", background='green')

        self.creer_ecrans()
        self.afficher_choix()

    def creer_ecrans(self):
        self.frame_choix = tk.Frame(self.fenetre)
        tk.Label(self.frame_choix, text="Que voulez-vous envoyer/reçevoir ?", font=("Arial", 12)).pack(pady=20)

        grille = tk.Frame(self.frame_choix)
        grille.pack()
        tk.Button(grille, text="TXT", width=12, command=lambda: self.afficher_saisie("TXT")).grid(row=0, column=0,
                                                                                                  padx=10, pady=10)
        tk.Button(grille, text="IMG", width=12, command=lambda: self.afficher_saisie("IMG")).grid(row=0, column=1,
                                                                                                  padx=10, pady=10)
        tk.Button(grille, text="TXT_REQ", width=12, command=lambda: self.afficher_saisie("TXT_REQ")).grid(row=1,
                                                                                                          column=0,
                                                                                                          padx=10,
                                                                                                          pady=10)
        tk.Button(grille, text="IMG_REQ", width=12, command=lambda: self.afficher_saisie("IMG_REQ")).grid(row=1,
                                                                                                          column=1,
                                                                                                          padx=10,
                                                                                                          pady=10)

        tk.Button(self.frame_choix, text="Annuler", command=self.fenetre.destroy).pack(side=tk.BOTTOM, pady=20)

        self.frame_saisie = tk.Frame(self.fenetre)
        self.lbl_saisie_titre = tk.Label(self.frame_saisie, text="", font=("Arial", 12))
        self.lbl_saisie_titre.pack(pady=10)

        self.frame_contenu_saisie = tk.Frame(self.frame_saisie)
        self.frame_contenu_saisie.pack(pady=10)

        frame_btn_saisie = tk.Frame(self.frame_saisie)
        frame_btn_saisie.pack(side=tk.BOTTOM, pady=20)
        tk.Button(frame_btn_saisie, text="Retour", command=self.afficher_choix).pack(side=tk.LEFT, padx=10)
        tk.Button(frame_btn_saisie, text="Valider et Envoyer", bg="lightblue", command=self.valider_saisie).pack(
            side=tk.LEFT, padx=10)

        self.frame_progression = tk.Frame(self.fenetre)
        self.lbl_envoi = tk.Label(self.frame_progression, text="Initialisation...", font=("Arial", 12))
        self.lbl_envoi.pack(pady=30)

        self.barre = ttk.Progressbar(self.frame_progression, style="green.Horizontal.TProgressbar", length=350,
                                     mode="indeterminate")
        self.barre.pack(pady=10)

        self.frame_reception = tk.Frame(self.fenetre)
        self.lbl_reception_prog = tk.Label(self.frame_reception, text="En attente de l'Arduino...",
                                           font=("Arial", 10, "bold"))
        self.lbl_reception_prog.pack(pady=(10, 0))

        self.barre_reception = ttk.Progressbar(self.frame_reception, style="green.Horizontal.TProgressbar", length=350,
                                               mode="determinate")
        self.barre_reception.pack(pady=10)

        tk.Label(self.frame_reception, text="Aperçu des données (Hex) :", font=("Arial", 9)).pack(pady=5)
        self.console_hex = scrolledtext.ScrolledText(self.frame_reception, width=50, height=10, bg="black",
                                                     fg="lightgreen")
        self.console_hex.pack(pady=5)

    def cacher_tout(self):
        self.frame_choix.pack_forget()
        self.frame_saisie.pack_forget()
        self.frame_progression.pack_forget()
        self.frame_reception.pack_forget()

    def afficher_choix(self):
        self.cacher_tout()
        self.frame_choix.pack(expand=True, fill=tk.BOTH)

    def afficher_saisie(self, type_envoi):
        self.type_actuel = type_envoi
        self.cacher_tout()
        for widget in self.frame_contenu_saisie.winfo_children():
            widget.destroy()

        if type_envoi == "TXT":
            self.lbl_saisie_titre.config(text="Tapez le texte à envoyer :")
            self.champ_texte = tk.Text(self.frame_contenu_saisie, height=8, width=40)
            self.champ_texte.pack()
        elif type_envoi == "IMG":
            self.lbl_saisie_titre.config(text="Sélectionnez l'image à envoyer :")
            self.champ_chemin = tk.Entry(self.frame_contenu_saisie, width=35, state="readonly")
            self.champ_chemin.pack(side=tk.LEFT, padx=5)
            tk.Button(self.frame_contenu_saisie, text="Parcourir...", command=self.choisir_fichier).pack(side=tk.LEFT)
        elif "REQ" in type_envoi:
            self.lbl_saisie_titre.config(text=f"Quel nom/ID demandez-vous ({type_envoi}) ?")
            self.champ_req = tk.Entry(self.frame_contenu_saisie, width=40)
            self.champ_req.pack()

        self.frame_saisie.pack(expand=True, fill=tk.BOTH)

    def choisir_fichier(self):
        chemin = filedialog.askopenfilename(title="Choisir une image",
                                            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp")])
        if chemin:
            self.champ_chemin.config(state="normal")
            self.champ_chemin.delete(0, tk.END)
            self.champ_chemin.insert(0, chemin)
            self.champ_chemin.config(state="readonly")

    def valider_saisie(self):
        if self.type_actuel == "TXT":
            contenu = self.champ_texte.get("1.0", tk.END).strip()
        elif self.type_actuel == "IMG":
            contenu = self.champ_chemin.get()
        elif "REQ" in self.type_actuel:
            contenu = self.champ_req.get().strip()

        if not contenu:
            messagebox.showwarning("Attention", "Veuillez remplir le champ avant d'envoyer.")
            return

        self.donnees_a_envoyer = contenu
        self.lancer_envoi(self.type_actuel)

    def lancer_envoi(self, type_envoi):
        self.type_actuel = type_envoi
        self.cacher_tout()
        self.lbl_envoi.config(text=f"Initialisation de l'Arduino pour {type_envoi}...")
        self.frame_progression.pack(expand=True, fill=tk.BOTH)

        if not self.ser or not self.ser.is_open:
            messagebox.showerror("Erreur", "Non connecté à l'Arduino.")
            self.fenetre.destroy()
            return

        self.barre.start(10)
        threading.Thread(target=self.tache_envoi_arriere_plan, daemon=True).start()

    def tache_envoi_arriere_plan(self):
        try:
            self.ser.reset_input_buffer()
            self.ser.write('send'.encode('ascii', 'ignore'))
            reponse = self.ser.readline().decode('ascii', 'ignore').strip()

            if reponse:
                self.fenetre.after(0, lambda: self.lbl_envoi.config(
                    text=f"Envoi de la trame {self.type_actuel} en cours..."))
                inp_str = f"/{self.type_actuel} {self.donnees_a_envoyer}"
                header, msg = generate_header(inp_str)

                if isinstance(header, str) and header in ["NO", "NOT"]:
                    self.fenetre.after(0, lambda: messagebox.showerror("Erreur", "Génération de l'en-tête échouée."))
                    self.fenetre.after(0, self.fenetre.destroy)
                    return

                to_trans = bytearray()
                to_trans.extend(header)
                to_trans.extend(msg)
                to_trans.append(255)

                send_with_handshake(self.ser, to_trans)

                while True:
                    line = self.ser.readline().decode('ascii', 'ignore').strip()
                    if line:
                        break

                self.fenetre.after(0, self.fin_envoi_succes)
            else:
                self.fenetre.after(0, lambda: messagebox.showerror("Erreur", "L'Arduino n'a pas répondu à 'send'."))
                self.fenetre.after(0, self.fenetre.destroy)
        except Exception as e:
            self.fenetre.after(0, lambda: messagebox.showerror("Erreur de communication", str(e)))
            self.fenetre.after(0, self.fenetre.destroy)
        finally:
            self.fenetre.after(0, self.barre.stop)

    def fin_envoi_succes(self):
        if "REQ" in self.type_actuel:
            self.preparer_reception()
        else:
            messagebox.showinfo("Succès", "La transmission est terminée.")
            self.fenetre.destroy()

    def preparer_reception(self):
        self.cacher_tout()
        self.frame_reception.pack(expand=True, fill=tk.BOTH)
        self.console_hex.delete(1.0, tk.END)
        self.barre_reception['value'] = 0
        self.hex_limit_atteinte = False

        # Lancement de la boucle de preview graphique à 30 Hz
        self.live_preview_active = True
        self.current_data_snapshot = bytearray()
        self.fenetre.after(33, self.boucle_live_preview)

        threading.Thread(target=self.tache_reception_arriere_plan, daemon=True).start()

    def boucle_live_preview(self):
        if not self.live_preview_active:
            return

        with self.current_data_lock:
            data_copy = bytearray(self.current_data_snapshot)

        # Si on reçoit bien une image (0xaa) et qu'on a déjà reçu l'en-tête et la palette complète (4 + 2 + 768 = 774 octets)
        if len(data_copy) >= 774 and data_copy[1] == 0xaa:
            try:
                L = data_copy[4]
                H = data_copy[5]

                if L > 0 and H > 0:
                    palette_bytes = data_copy[6:774]
                    # Formatage de la palette en RGB
                    palette = np.frombuffer(palette_bytes, dtype=np.uint8).reshape(256, 3)

                    pixel_bytes = data_copy[774:]
                    expected_pixels = L * H
                    current_pixels = len(pixel_bytes)

                    # Remplissage intelligent : les pixels non reçus sont remplis de "0" (la première couleur de la palette)
                    if current_pixels < expected_pixels:
                        pixel_bytes += bytearray([0] * (expected_pixels - current_pixels))
                    elif current_pixels > expected_pixels:
                        pixel_bytes = pixel_bytes[:expected_pixels]

                    # Construction de l'image partielle
                    indices = np.frombuffer(pixel_bytes, dtype=np.uint8)
                    img_preview = palette[indices]
                    img_preview = img_preview.reshape((H, L, 3))

                    # Convertir RGB vers BGR pour un affichage correct dans OpenCV
                    img_preview = cv2.cvtColor(img_preview, cv2.COLOR_RGB2BGR)

                    # Affichage fluide avec OpenCV !
                    cv2.imshow("Reception en direct...", img_preview)
                    cv2.waitKey(1)
            except Exception as e:
                pass  # On ignore silencieusement si un paquet partiel rend l'opération instable le temps d'une frame

        # Re-planifie cette fonction pour dans 33ms (~30 FPS)
        if self.live_preview_active:
            self.fenetre.after(33, self.boucle_live_preview)

    def set_barre_reception_max(self, max_val):
        self.barre_reception.config(maximum=max_val)
        self.lbl_reception_prog.config(text=f"Réception : 0 / {max_val} octets")

    def update_barre_reception(self, current, max_val):
        self.barre_reception['value'] = current
        self.lbl_reception_prog.config(text=f"Réception : {current} / {max_val} octets")

    def gerer_timeout_arduino(self):
        # On ferme proprement la prévisualisation en direct au cas où
        try:
            cv2.destroyWindow("Reception en direct...")
        except:
            pass

        # Affichage du message d'erreur
        messagebox.showwarning("Timeout",
                               "L'Arduino a déclaré un timeout (aucune donnée trouvée ou reçue à temps).\nOpération annulée.")

        # Fermeture de la fenêtre d'envoi/réception
        self.fenetre.destroy()

    def tache_reception_arriere_plan(self):
        global im, txt, data_cont

        receiving = True
        num_taken = False
        first_val_taken = False
        n_lsb = 0
        n_msb = 0
        n_payload = 0
        data = bytearray()
        last_receive_time = time.time()

        self.ser.timeout = 0.5

        while receiving:
            bytes_to_read = max(self.ser.in_waiting, 1)
            c = self.ser.read(bytes_to_read)

            if c:
                data.extend(c)
                last_receive_time = time.time()

                # ---- Prise de la snapshot pour le Live Preview ----
                with self.current_data_lock:
                    self.current_data_snapshot = data
                # --------------------------------------------------

                if not first_val_taken and len(data) > 0:
                    if data[0] == 9:
                        print("Timeout côté Arduino.")
                        # On demande au thread principal d'afficher l'erreur et de fermer la fenêtre
                        self.fenetre.after(0, self.gerer_timeout_arduino)
                        receiving = False
                        break
                    elif data[0] == 128:
                        first_val_taken = True

                if len(data) >= 4 and not num_taken:
                    n_lsb = data[2]
                    n_msb = data[3]
                    n_payload = n_msb * 256 + n_lsb
                    num_taken = True
                    self.fenetre.after(0, self.set_barre_reception_max, n_payload + 4)

                if num_taken:
                    self.fenetre.after(0, self.update_barre_reception, len(data), n_payload + 4)

                if not self.hex_limit_atteinte:
                    if len(data) < 200:
                        new_hex = [f"{b:02X}" for b in c]
                        chunk = " ".join(new_hex) + " "
                        self.fenetre.after(0, self.ajouter_hexa_console, chunk)
                    else:
                        self.hex_limit_atteinte = True
                        self.fenetre.after(0, self.ajouter_hexa_console,
                                           "\n\n... [Fin de l'affichage Hex pour empêcher la perte de données] ...")

                if num_taken and len(data) >= 4 + n_payload:
                    receiving = False
                    data_nette = data[:4 + n_payload]
                    self.fenetre.after(0, self.traiter_decodage, data_nette)
                    break
            else:
                if receiving and last_receive_time is not None:
                    elapsed = time.time() - last_receive_time
                    if elapsed > 2.0:
                        if num_taken and len(data) < n_payload + 4:
                            print(f"Perte de données : reçu {len(data)} / {n_payload + 4}")
                            while len(data) < n_payload + 4:
                                data.append(0x00)
                            self.fenetre.after(0, self.traiter_decodage, data)
                        receiving = False
                        break

        # Arrêt du Live Preview en douceur pour le thread d'arrière plan
        self.live_preview_active = False

        self.ser.write('stop'.encode('ascii', 'ignore'))
        self.ser.timeout = 1

    def ajouter_hexa_console(self, texte):
        self.console_hex.insert(tk.END, texte)
        self.console_hex.see(tk.END)

    def traiter_decodage(self, data):
        global im, txt, data_cont
        type_fichier = None

        try:
            if data[1] == 0xaa:
                im = process_packet(data)
                type_fichier = "IMG"
            elif data[1] == 0x8f:
                txt = process_packet(data)
                type_fichier = "TXT"
            else:
                process_packet(data)
                data_cont = data
                type_fichier = "INCONNU"
        except Exception as e:
            messagebox.showerror("Erreur de décodage", str(e))

        self.demander_affichage_final(type_fichier)

    def demander_affichage_final(self, type_fichier):
        # On ferme proprement la fenêtre OpenCV de prévisualisation dans le thread principal
        try:
            cv2.destroyWindow("Reception en direct...")
        except:
            pass

        if type_fichier == "IMG":
            choix = messagebox.askyesno("Terminé",
                                        "La trame d'image a été entièrement reçue et reconstruite.\nL'afficher en pleine résolution ?")

            # On détruit la fenêtre de menu AVANT d'attendre OpenCV
            self.fenetre.destroy()

            if choix:
                try:
                    # --- NOUVELLES LIGNES POUR L'UPSCALE x4 ---
                    # On récupère les dimensions actuelles
                    h, w = im.shape[:2]

                    # On redimensionne x4.
                    # INTER_NEAREST empêche l'image de devenir floue (garde le côté "pixel net")
                    im_upscaled = cv2.resize(im, (w * 3, h * 3), interpolation=cv2.INTER_NEAREST)

                    cv2.imshow("Image Finale Complete (Upscale x3)", im_upscaled)
                    # ------------------------------------------

                    cv2.waitKey(0)
                    cv2.destroyAllWindows()
                except Exception as e:
                    # J'ai ajouté 'e' pour que tu puisses voir l'erreur exacte si ça plante
                    messagebox.showerror("Erreur OpenCV", f"Impossible d'ouvrir l'image.\n{e}")
        elif type_fichier == "TXT":
            messagebox.showinfo("Texte Reçu", txt)
            self.fenetre.destroy()
        else:
            messagebox.showwarning("Fichier inconnu",
                                   "Les données brutes ont été reçues mais ne sont pas affichables directement.")
            self.fenetre.destroy()


# --- Lancement ---
if __name__ == "__main__":
    root = tk.Tk()
    app = ApplicationPrincipale(root)
    root.mainloop()