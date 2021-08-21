#!/bin/sh
echo -en "$(curl -s --compressed 'ftp://ftp.nasdaqtrader.com/SymbolDirectory/nasdaqlisted.txt' | tail -n+2 | head -n-1 | perl -pe 's/ //g' | tr '|' ' ' | awk '{print}')"