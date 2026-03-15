from tkinter import *
from tkinter.messagebox import *
from Communication.traitement_img import *
from Communication.trans_arduino import *
import subprocess


def Changement_Fenetres(fenetre_actuelle, fonction_ouverture):
    fenetre_actuelle.withdraw()
    fonction_ouverture()


def fermer(fenetre_principale) :
    reponse = askyesno('Fermeture', 'Voulez vous fermer le programme')

    if reponse :
        fenetre_principale.destroy()

def retour(fenetre_actuelle, fenetre_principale) :
    fenetre_actuelle.destroy()
    fenetre_principale.deiconify()

def commande_terminal(commande):
    try :
        subprocess.run(commande, sheel=True)
    except Exception as e :
        print(f"Erreur : {e}")