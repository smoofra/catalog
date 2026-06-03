
# brew install csvkit unix2dos

.PHONY: import

import:
	csvstack catalog.csv cardex.csv | unix2dos >tmp.csv
	mv tmp.csv catalog.csv