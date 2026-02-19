# HRMS Lite

## Overview
A lightweight Human Resource Management System allowing admin to manage employees and track attendance.

## Tech Stack
Frontend: Angular
Backend: FastAPI
Database: PostgreSQL (Neon)
Deployment: Render (API), Render (Frontend)

## Features
- Add, list, delete employees
- Mark attendance
- Attendance history
- Dashboard summary

## Default Admin Credentials
Phone Number: 9999988888
Password: Yashdeep@123

## Local Setup

Backend:
1. pip install -r requirements.txt
2. alembic upgrade head
3. uvicorn app.main:app --reload

Frontend:
1. npm install
2. ng serve

## Assumptions
- Single admin user
- No payroll or leave management
- No multi-company support
