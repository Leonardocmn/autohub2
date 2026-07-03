# Architecture Design

## System Overview
Vehicle intermediation management platform (CRM) with admin panel for managing offers, suppliers, buyers, categories, distribution, and negotiation tracking. Built as a full-stack web application with React frontend and Atoms Cloud backend.

## Tech Stack
- Frontend: React + TypeScript + Vite + Tailwind CSS + Shadcn/ui
- Backend: Atoms Cloud (Auth, Database, Object Storage)
- Database: PostgreSQL via Atoms Cloud entities
- Auth: Atoms Cloud built-in authentication
- Storage: Object Storage for vehicle images

## Module Design
| Module | Responsibility | Key Files |
|--------|---------------|-----------|
| Auth | Login/logout, session management | LoginPage.tsx, App.tsx (ProtectedRoute) |
| Dashboard | Overview stats, recent offers | pages/Index.tsx |
| Suppliers | CRUD for vehicle suppliers | pages/SuppliersPage.tsx |
| Buyers | CRUD for buyers with categories | pages/BuyersPage.tsx |
| Categories | Manage buyer categories | pages/CategoriesPage.tsx |
| Offers | Full offer lifecycle management | pages/OffersPage.tsx |
| Distribution | Distribute offers to buyer categories | pages/DistributionPage.tsx |
| Negotiations | Track negotiation status workflow | pages/NegotiationsPage.tsx |
| Negotiation Numbers | Manage WhatsApp numbers | pages/NegotiationNumbersPage.tsx |
| History | View finalized offers | pages/HistoryPage.tsx |
| Layout | Sidebar navigation, responsive | components/AppLayout.tsx |

## Tech Decisions
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend | Atoms Cloud | Built-in auth, database, storage |
| State management | React Query + local state | Simple CRUD operations |
| Routing | React Router v6 | Standard SPA routing |
| UI Components | Shadcn/ui | Pre-built, accessible components |
| Data access | Web SDK entities | Direct CRUD without custom APIs |

## File Tree Plan
```
app/frontend/src/
├── App.tsx (routes + auth guard)
├── components/
│   └── AppLayout.tsx (sidebar + header)
├── pages/
│   ├── Index.tsx (dashboard)
│   ├── LoginPage.tsx
│   ├── SuppliersPage.tsx
│   ├── BuyersPage.tsx
│   ├── CategoriesPage.tsx
│   ├── OffersPage.tsx
│   ├── DistributionPage.tsx
│   ├── NegotiationsPage.tsx
│   ├── NegotiationNumbersPage.tsx
│   └── HistoryPage.tsx
├── lib/
│   └── api.ts (web-sdk client)
└── index.css (theme tokens)
```

## Implementation Guide
1. Database tables created via BackendManager (8 tables)
2. Object storage bucket for vehicle images
3. Frontend uses web-sdk client.entities for all CRUD
4. Auth via client.auth.me() / toLogin() / logout()
5. Protected routes redirect to /login if unauthenticated
6. Negotiation workflow: awaiting_update -> negotiated (entered/not_entered) or not_negotiated
7. Distribution with deduplication logic in frontend