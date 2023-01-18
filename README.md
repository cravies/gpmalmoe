Usage (from the src/ directory):   
To run on iris.data (in /src/datasets dir) for 10 generations, using functional minimisation 
as our seconday objective to minimise (alongside neighbourhood structure embedding loss)
```bash
make run DATASET=iris GENS=3 OBJ=functional DIR="./datasets/"
```
To clean up output files in the directory:
```bash
make clean
```
To run (non exhaustive) tests
```
make test
```

Note:
* Datasets used in the paper are in datasets/
* Add your own datasets in csv format, with a header line:  
Header: classPosition,#features,#classes,seperator. e.g.  
`classLast,1024,20,comma (from COIL20.data)`
* Most GP parameters are configured in gpmalmo/rundata.py
