#!/usr/bin/env bash
coverage run -m pytest . -v -m "not integration"
