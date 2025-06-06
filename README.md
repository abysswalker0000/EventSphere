# EventSphere
  EventSphere is a web application designed to facilitate event organization and participation. The platform allows users to create, manage, and attend events, with features like event recommendations based on past attendance, social interactions, and ticket sales.

## Schema
![Functional_scheme](https://github.com/user-attachments/assets/2346d012-2e8d-4346-acb7-413365259f2d)


## Models
- **User**  
  - `id` (PK)  
  - `email`  
  - `name`  
  - `bio`  
  - `role` (enum: user, organizer, admin)  
  - `created_at`

- **Event**  
  - `id` (PK)  
  - `title`  
  - `description`  
  - `event_date`  
  - `location`  
  - `category_id` (FK to Category)  
  - `organizer_id` (FK to User)  
  - `created_at`

- **Category**  
  - `id` (PK)  
  - `name`

- **Participation**  
  - `id` (PK)  
  - `user_id` (FK to User)  
  - `event_id` (FK to Event)  
  - `status` (enum: going, interested, not going)  
  - `joined_at`

- **Comment**  
  - `id` (PK)  
  - `event_id` (FK to Event)  
  - `user_id` (FK to User)  
  - `text`  
  - `created_at`

- **Review**  
  - `id` (PK)  
  - `event_id` (FK to Event)  
  - `user_id` (FK to User)  
  - `rating` (int)  
  - `comment`  
  - `created_at`

- **Ticket**  
  - `id` (PK)  
  - `event_id` (FK to Event)  
  - `user_id` (FK to User)  
  - `price`  
  - `purchased_at`

- **Subscription**  
  - `id` (PK)  
  - `follower_id` (FK to User)  
  - `followee_id` (FK to User)  
  - `created_at`

## Functionality
- User registration and authentication
- Profile management (name, bio, photo, interests, event history, rating)
- Event creation and management (title, description, date, location, category)
- Event Participation  (join, show interest, or ignore events)
- Event discussions (chat or forum)
- Notifications with customizable frequency
- Advanced search (by category, date, location)
- Event recommendations (based on interests, past events, friends)
- Social features (friends, subscriptions to organizers)
- Reviews and ratings for events and organizers
- Paid events (ticket sales, access control)
- Event promotion for organizers
- Analytics for organizers (participants, views, reviews)
