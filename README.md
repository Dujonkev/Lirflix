# Lirflix — intégration Home Assistant

Suivi des nouveaux épisodes publiés sur lirflix.net, directement dans
Home Assistant.

## Pourquoi cette intégration ?

Un capteur par émission suivie, avec en état le numéro du dernier
épisode publié, et un événement `lirflix_new_episode` déclenché à chaque
nouvelle parution — pratique pour une notification automatique dès
qu'un épisode sort.

Seul le flux public de métadonnées du site (`data/shows.json`) est
interrogé : titre de l'émission, numéro et titre du dernier épisode,
jour/heure de diffusion habituelle. L'intégration n'accède jamais aux
liens de lecture ou de téléchargement des épisodes et ne les expose pas.

## Fonctionnalités

- Un capteur `sensor.<émission>` par émission suivie : état = numéro du
  dernier épisode, attributs = titre de l'épisode, jour/heure de
  diffusion, nombre total d'épisodes disponibles, URL de la page de
  l'émission.
- Événement `lirflix_new_episode` (slug, titre de l'émission, numéro et
  titre de l'épisode, URL) à chaque nouvelle parution détectée.
- Sélection des émissions suivies et intervalle de vérification
  configurables depuis l'interface, modifiables à tout moment sans
  recréer l'intégration.

## Prérequis

- Home Assistant 2024.12 ou plus récent.

## Installation

### Via HACS (dépôt personnalisé)

1. HACS → menu ⋮ → **Dépôts personnalisés**
2. URL : `https://github.com/Dujonkev/Lirflix`, catégorie : **Integration**
3. Rechercher **Lirflix**, installer, puis redémarrer Home Assistant
4. **Paramètres → Appareils et services → Ajouter une intégration →
   Lirflix**

### Manuellement

Copier le dossier `custom_components/lirflix` dans le dossier
`custom_components` de votre configuration, redémarrer Home Assistant,
puis ajouter l'intégration.

## Configuration

Sélectionnez les émissions à suivre (ex : "Les Apprentis Aventuriers",
"Koh Lanta All Stars"...) et l'intervalle de vérification souhaité
(20 minutes par défaut). Modifiable ensuite via **Paramètres →
Appareils et services → Lirflix → Configurer**.

## Exemple : notification à la sortie d'un épisode

```yaml
alias: "Nouvel épisode Lirflix"
trigger:
  - platform: event
    event_type: lirflix_new_episode
action:
  - service: notify.mobile_app_votre_telephone
    data:
      title: "Nouvel épisode disponible"
      message: >
        {{ trigger.event.data.show_title }} - {{ trigger.event.data.episode_title }}
      data:
        url: "{{ trigger.event.data.url }}"
```

Filtrez sur une émission précise avec une condition sur
`trigger.event.data.slug` (ex : `laa9`).

## Dépannage

- **Une émission n'apparaît pas** : vérifiez qu'elle existe toujours
  dans `https://lirflix.net/data/shows.json` sous le même identifiant.
- **Le capteur ne se met pas à jour** : consultez les journaux Home
  Assistant, `data/shows.json` n'est pas une API officiellement
  documentée par le site et son format peut changer sans préavis.
- Journaux détaillés :
  ```yaml
  logger:
    default: warning
    logs:
      custom_components.lirflix: debug
  ```

## Limites volontaires

Aucune donnée de lecture ou de téléchargement (liens de streaming,
hébergeurs de fichiers) n'est récupérée ni exposée : seule
l'information « un épisode X est sorti » est fournie, à l'image d'un
guide TV. Le lien fourni (`url`) pointe vers la page publique de
l'émission, pas vers un flux de lecture.

## Avertissement

Projet personnel, non affilié à lirflix.net. lirflix.net référence des
liens de lecture/téléchargement vers des rediffusions d'émissions de
télévision dont le statut au regard du droit d'auteur n'est pas
garanti ; cette intégration ne fait que lire les métadonnées publiques
d'annonce du site (titres, numéros d'épisodes, planning) et n'héberge,
ne relaie ni ne facilite l'accès à aucun contenu protégé. Utilisez-la
en connaissance de cause.

Sous licence MIT.
