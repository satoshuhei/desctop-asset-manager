# Basic Design

## Overview
Desktop Asset Manager is a Tkinter desktop application with a layered architecture:
- UI layer (Tkinter views)
- Service layer (business operations)
- Repository layer (SQLite persistence)
- Infra layer (DB initialization and seed data)

## UI Structure
### Top-Level Navigation
- Assets tab
  - Devices (Redmine-style ticket form + list)
  - Licenses (Redmine-style ticket form + list)
- Configurations tab
  - Left: device/license lists (for drag source)
  - Right: configuration board with cards (drag target)

### Device List View
- Form fields: Asset No (required), Subject, Type, Model, Version, Status, Description
- Search filter: keyword filter on subject/label
- List presentation: TreeView with columns (Subject, Asset No, Type, Model, Version, Status)

### License List View
- Form fields: Subject (required), License Key, Status, Description
- Search filter: keyword filter on subject
- List presentation: TreeView with columns (Subject, License Key, Status)

### Configuration Board
- Toolbar to add configurations
- Scrollable card layout
- Each ConfigCard shows device and license listboxes
- Drag-and-drop from left lists to card listboxes

### Drag and Drop Feedback
- Drag preview (ghost label) follows cursor
- Drop target listbox highlights on hover

## Service Layer
### AssetService
- Create device
- List devices
- Create license
- List licenses

### ConfigService
- Create configuration
- List configurations
- Rename configuration
- Assign/unassign device/license
- Move device between configurations

## Repository Layer
### DeviceRepository / LicenseRepository / ConfigRepository
- CRUD operations for devices, licenses, and configurations
- Linking tables for configuration-device/license relationships

## Infra Layer
### init_db
- Creates all tables
- Seeds sample data when devices/licenses are empty

## Key Interactions
- App startup initializes DB, repositories, services, then builds UI
- Asset creation triggers list refresh in both Assets and Configurations tabs
- Drag-and-drop assigns devices/licenses to configuration cards and refreshes lists
