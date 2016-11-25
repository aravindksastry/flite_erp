#!/bin/bash
PGPASSWORD="admin" /usr/bin/pg_dump  -U postgres -F custom featherlite > featherlite.backup