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
- Un capteur global `sensor.lirflix_nouveaux_episodes` (dès que plus
  d'une émission est suivie) : état = nombre d'épisodes pas encore
  acquittés, tous suivis confondus, avec en attributs la liste des
  émissions concernées et le titre de la dernière détectée. Le service
  `lirflix.mark_all_seen` (voir plus bas) remet ce compteur à zéro.
- Une entité calendrier `calendar.lirflix_planning` qui présente, pour
  chaque émission suivie, le jour et l'heure de diffusion habituels tels
  qu'annoncés sur le site (créneau récurrent de 30 minutes, purement
  indicatif : ce n'est pas une confirmation qu'un épisode précis sera
  diffusé à une date donnée). S'affiche directement dans les vues
  Calendrier de Home Assistant.
- Événement `lirflix_new_episode` (slug, titre de l'émission, numéro et
  titre de l'épisode, URL) à chaque nouvelle parution détectée.
- Service `lirflix.mark_all_seen` pour acquitter manuellement les
  derniers épisodes connus (toutes émissions, ou une seule entrée de
  configuration via le champ optionnel `config_entry_id`).
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

## Exemple : acquitter tous les nouveaux épisodes

```yaml
service: lirflix.mark_all_seen
```

Ou pour une seule entrée de configuration (utile si plusieurs entrées
Lirflix sont configurées) :

```yaml
service: lirflix.mark_all_seen
data:
  config_entry_id: "01ABCXYZEXEMPLE"
```

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
l'émission, pas vers un flux de lecture. Il en va de même pour le
calendrier : le jour/heure affiché est celui annoncé publiquement pour
la diffusion habituelle de l'émission, pas une donnée issue des liens
de lecture.

## Avertissement

Projet personnel, non affilié à lirflix.net. lirflix.net référence des
liens de lecture/téléchargement vers des rediffusions d'émissions de
télévision dont le statut au regard du droit d'auteur n'est pas
garanti ; cette intégration ne fait que lire les métadonnées publiques
d'annonce du site (titres, numéros d'épisodes, planning) et n'héberge,
ne relaie ni ne facilite l'accès à aucun contenu protégé. Utilisez-la
en connaissance de cause.

Sous licence MIT.
