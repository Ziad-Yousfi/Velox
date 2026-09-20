<div align="center">
  <p align="center">
    <a href="README.md"><img src="https://img.shields.io/badge/Language-English-lightgrey?style=for-the-badge&logo=google-translate&logoColor=white" alt="English" /></a>
    <a href="README.fr.md"><img src="https://img.shields.io/badge/Langue-Français-00D4FF?style=for-the-badge&logo=google-translate&logoColor=white" alt="Français" /></a>
  </p>
  <p align="center">
    <b><a href="README.md">🇬🇧 Switch to English</a></b> &nbsp;•&nbsp; <b>🇫🇷 Version Française</b>
  </p>

  <img src="gaming-launcher/icon/velox_icon.jpg" alt="Velox Gaming Launcher Logo" width="190" style="border-radius: 22px; box-shadow: 0 10px 30px rgba(0,0,0,0.6);" />
  <h1>⚡ VELOX GAMING LAUNCHER</h1>
  <p><strong>Lanceur de jeux ultra-léger, performant et élégant pour Windows avec suivi automatique du temps de jeu et statistiques avancées.</strong></p>

  <p>
    <img src="https://img.shields.io/badge/Version-1.0.0-00D4FF?style=for-the-badge" alt="Version" />
    <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
    <img src="https://img.shields.io/badge/GUI-PyQt6-41CD52?style=for-the-badge&logo=qt&logoColor=white" alt="PyQt6" />
    <img src="https://img.shields.io/badge/Database-SQLite_WAL-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite" />
    <img src="https://img.shields.io/badge/RAM-~45MB_Idle-yellow?style=for-the-badge" alt="RAM" />
    <img src="https://img.shields.io/badge/Author-Ziad--Yousfi-7B2FFF?style=for-the-badge" alt="Auteur" />
    <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License" />
  </p>

  <p>
    <a href="https://github.com/Ziad-Yousfi/Velox/releases/download/v1.0.0/Velox.exe">
      <img src="https://img.shields.io/badge/⚡_Télécharger_Velox.exe-v1.0.0-00D4FF?style=for-the-badge&logo=windows&logoColor=white" alt="Télécharger Velox.exe" />
    </a>
    <a href="https://github.com/Ziad-Yousfi/Velox/releases">
      <img src="https://img.shields.io/badge/📦_GitHub-Releases-7B2FFF?style=for-the-badge&logo=github&logoColor=white" alt="Releases" />
    </a>
  </p>
</div>

---

## 📖 À Propos de Velox

**Velox** (*« véloce, rapide, agile »* en latin) est un lanceur de jeux vidéo indépendant conçu pour offrir une alternative réactive, moderne et économe en ressources face aux clients de jeux lourds et énergivores.

Inspiré par **Mercure (Mercurius)** — dieu romain de la vitesse coiffé de son casque ailé et revisité sous un prisme cyberpunk —, Velox fusionne l'art néo-classique et la vélocité technologique.

---

## ✨ Fonctionnalités Clés

### 🎮 Gestion de la Bibliothèque
* **Grille responsive et dynamique** : Présentation claire de vos jeux avec pochettes personnalisées, titres éditables et raccourcis d'action rapide.
* **Ajout flexible de jeux** :
  * Détection et scan automatique d'exécutables dans un dossier cible.
  * Ajout manuel avec sélection de l'exécutable (`.exe`) et association d'une jaquette dédiée.
* **Gestion complète (CRUD)** : Modification du nom, mise à jour de l'image de couverture ou suppression d'un jeu via le bouton paramètres de chaque carte.

### ⏱️ Suivi Automatique du Temps de Jeu
* **Détection automatique en arrière-plan** : Dès que vous lancez un jeu depuis Velox, le processus est tracé sans aucune latence via son PID.
* **Enregistrement de sessions précises** : Horodatage précis (date, heure de début, heure de fin, durée en secondes) consigné dans la base SQLite locale.
* **Zéro blocage d'interface** : Le moteur de surveillance tourne dans un thread dédié ultra-léger avec un intervalle de polling intelligent de 5 secondes.

### 📊 Analyses & Statistiques Détaillées
Velox intègre deux niveaux de statistiques complètes :

#### 1. Statistiques Individuelles par Jeu
* **Graphique 30 jours** : Barres interactives avec dégradé visuel illustrant le temps joué quotidiennement.
* **Calendrier Heatmap** :
  * Visualisation mensuelle par niveau d'intensité (5 nuances de couleurs).
  * Affichage direct et lisible du temps passé (ex: `1h 45m` ou `35m`) au cœur de chaque case journalière.
  * Navigation fluide mois par mois et détail précis des sessions.

#### 2. Statistiques Globales de la Bibliothèque
* **Repère Orthogonal à 2 Axes (X = Jeux / Y = Heures)** : Comparateur graphique direct du temps cumulé entre tous vos jeux avec échelle adaptative et infobulles au survol.
* **Vue Combinée & KPIs Clés** :
  * ⏱️ *Temps cumulé total* de toute la bibliothèque.
  * 🎮 *Nombre total de jeux* enregistrés.
  * 🎯 *Sessions jouées*.
  * ⏳ *Durée moyenne* par partie.
  * 🏆 *Jeu favori* et son pourcentage d'occupation.
  * 📈 *Activité globale quotidienne sur 30 jours*.
  * 📊 *Tableau de répartition complète* par jeu avec jauges de progression.

### 🎨 Moteur Multi-Thèmes Dynamique
* Sélecteur de thèmes accessible dans les paramètres :
  * **Velox Cyberpunk** (Sombre électrique néon cyan & violet).
  * **Solarized Light** (Palette claire haut contraste `#FDF6E3`, lisibilité maximale, survol jaune foncé doré `#D4A017` sur les cartes).
  * **Obsidian Dark** & variantes.
* Respect immédiat du thème actif sur l'ensemble des fenêtres, dialogues, cartes et graphiques.

### 🛡️ Gestion Intelligente du Systray & Fermeture Sécurisée
Velox distingue la mise en retrait et l'extinction complète :
* **Bouton Fermer (✕) ou Alt+F4** : Ferme la fenêtre graphique (`hide()`). L'application reste active dans la barre des tâches / zone de notification Windows (systray) avec son icône transparente de Mercure. Le tracking du temps de jeu continue sans interruption. Un simple clic sur l'icône restaure instantanément la fenêtre.
* **Bouton Éteindre (⏻)** : Situé dans la barre de titre et dans le menu contextuel du systray, il assure un arrêt propre et sécurisé de tous les threads, de la base de données et du processus en tâche de fond.

---

## 🛠️ Architecture & Choix Technologiques

| Composant | Technologie | Rationale & Bénéfices |
|-----------|------------|-----------------------|
| **Framework Graphique** | **PyQt6 (Qt 6 C++)** | Rendu natif GPU, composants fluides, consommation RAM ~10x inférieure à Electron (~45 Mo vs ~250 Mo). |
| **Base de Données** | **SQLite 3 (Mode WAL)** | Sans configuration serveur, requêtes en cache mémoire, concurrence de lecture/écriture instantanée. |
| **Moteur de Graphiques** | **Custom QPainter 2D** | Zéro dépendance lourde externe (pas de matplotlib lourd), graphiques vectoriels anti-aliasés ultra-rapides. |
| **Tracking Processus** | **Threading + Win32 PID** | Surveillance non-bloquante avec cycle de veille 5s : impact CPU inférieur à 0.1%. |
| **Identité Windows** | **Win32 AppUserModelID** | Intégration native dans la barre des tâches Windows 10/11 sans icône Python générique. |

---

## 📁 Structure du Projet

```
Velox/
├── README.md                     # Documentation en anglais (par défaut)
├── README.fr.md                  # Documentation en français
├── Velox.exe                     # Exécutable autonome compilé
├── .gitignore
└── gaming-launcher/
    ├── Velox.spec                # Configuration de compilation PyInstaller
    ├── main.py                   # Point d'entrée, initialisation Qt, polices & icône
    ├── requirements.txt          # Dépendances Python (PyQt6, Pillow)
    ├── icon/                     # Identité visuelle officielle
    │   ├── velox_icon.jpg        # Illustration originale haute définition
    │   ├── velox_icon_transparent.png# Emblème détouré (fond transparent pur)
    │   ├── velox.ico             # Icône Windows multi-résolutions (16px à 256px)
    │   └── velox_transparent.ico # Icône transparente pour le systray
    ├── assets/
    │   ├── fonts/                # Polices embarquées (Rajdhani)
    │   └── icons/                # Déclinaisons d'icônes
    ├── core/                     # Logique métier & Données
    │   ├── database.py           # Abstraction SQLite avec pool & cache 5s
    │   ├── models.py             # Modèles de données (Game, Session)
    │   ├── theme.py              # Système de thèmes dynamiques & palettes
    │   └── tracker.py            # Surveillance et suivi de processus
    └── ui/                       # Interface Utilisateur PyQt6
        ├── main_window.py        # Fenêtre principale frameless & barre de titre
        ├── game_card.py          # Carte de jeu individuelle (hover, stats, play)
        ├── stats_window.py       # Statistiques d'un jeu (graphique 30j + heatmap)
        ├── global_stats_window.py# Statistiques globales (repère orthogonal + combinées)
        ├── add_game_dialog.py    # Dialogue d'ajout / détection de jeux
        └── edit_game_dialog.py   # Dialogue de modification et suppression
```

---

## 🚀 Installation & Démarrage

### Option A : Téléchargement Direct (Recommandé - Aucun Python requis)
1. Rendez-vous sur la page des [Releases Velox v1.0.0](https://github.com/Ziad-Yousfi/Velox/releases/tag/v1.0.0).
2. Téléchargez **[Velox.exe](https://github.com/Ziad-Yousfi/Velox/releases/download/v1.0.0/Velox.exe)**.
3. Lancez directement l'application !

---

### Option B : Exécution depuis les Sources Python

#### Prérequis
* **Système d'exploitation** : Windows 10 ou Windows 11 (64-bit).
* **Python** : Version 3.10 ou supérieure installée ([python.org](https://www.python.org/)).

#### Étape 1 : Cloner le Répertoire
```bash
git clone https://github.com/Ziad-Yousfi/Velox.git
cd Velox/gaming-launcher
```

#### Étape 2 : Créer un Environnement Virtuel (Recommandé)
```bash
python -m venv venv
.\venv\Scripts\activate
```

#### Étape 3 : Installer les Dépendances
```bash
pip install -r requirements.txt
```

#### Étape 4 : Lancer Velox
```bash
python main.py
```

---

## 🏗️ Compilation en Exécutable Autonome (`.exe`)

Le projet inclut un fichier de configuration PyInstaller optimisé ([Velox.spec](file:///e:/Documents/Developpement/Actif/Velox/gaming-launcher/Velox.spec)) :

```bash
# 1. Se placer dans le dossier gaming-launcher
cd gaming-launcher

# 2. Compiler avec le fichier de spec
pyinstaller Velox.spec --clean --noconfirm
```

L'exécutable généré se trouvera dans le dossier `dist/Velox.exe`.

---

## 🎮 Guide d'Utilisation Rapide

| Action | Comment faire ? |
|--------|-----------------|
| **Ajouter un jeu** | Cliquez sur `+ AJOUTER` dans la barre supérieure, sélectionnez le fichier `.exe` et une image de couverture. |
| **Lancer un jeu** | Cliquez sur le bouton `▶ JOUER` de la carte. Le chronométrage démarre immédiatement. |
| **Consulter les stats d'un jeu** | Cliquez sur l'icône graphique `📊` à côté du bouton Jouer sur la carte. |
| **Consulter les stats globales** | Cliquez sur `📊` dans la barre supérieure pour afficher le comparatif orthogonal et les KPIs combinés. |
| **Changer de thème** | Cliquez sur l'icône engrenage `⚙` pour choisir entre les modes sombre, clair ou cyberpunk. |
| **Réduire en tâche de fond** | Cliquez sur la croix `✕` de la fenêtre : Velox continue d'enregistrer votre temps de jeu dans le systray. |
| **Quitter définitivement** | Cliquez sur l'icône rouge d'extinction `⏻` dans la barre de titre ou via le clic-droit sur l'icône systray. |

---

## 👤 Auteur & Contact

* **Auteur** : [Ziad Yousfi](https://github.com/Ziad-Yousfi)
* **Email** : `yousfiziadpro@gmail.com`
* **Projet** : [Velox Gaming Launcher](https://github.com/Ziad-Yousfi/Velox)

---

## 📄 Licence

Ce projet est sous licence **MIT**. Vous êtes libre de l'utiliser, l'étudier, le modifier et le distribuer.
