from tkinter import *
from fonctions import Changement_Fenetres, retour

def ouvrir_Parametres(fenetre_principale) :
    fenetre_Parametres = Toplevel(fenetre_principale)
    fenetre_Parametres.state('zoomed')

    titre = Label(fenetre_Parametres, text="Paramètres")

    bouton_retour = Button(fenetre_Parametres, text='Retour', command=lambda: retour(fenetre_Parametres, fenetre_principale) )

    bouton_retour.pack(pady=50)