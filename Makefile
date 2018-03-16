all: execute_GBN execute_ABP_NAK execute_ABP

execute_GBN: run_GBN.sh
	./run_GBN.sh

execute_ABP: run_ABP.sh
	./run_ABP.sh

execute_ABP_NAK: run_ABP_NAK.sh
	./run_ABP_NAK.sh

run_GBN.sh: main.py
	@echo "python main\.py 3" > run_GBN.sh
	chmod 777 run_GBN.sh

run_ABP.sh: main.py
	@echo "python main\.py 1" > run_ABP.sh
	chmod 777 run_ABP.sh

run_ABP_NAK.sh: main.py
	@echo "python main\.py 2" > run_ABP_NAK.sh
	chmod 777 run_ABP_NAK.sh
