
### This code is associated with the paper from Galardini et al., "Phenotype inference in an Escherichia coli strain panel". eLife, 2017. http://dx.doi.org/10.7554/eLife.31035

screenings
=========

Chemical genetic data analysis pipeline for the *Escherichia coli*
genetic reference panel (EcoRef). The phenotypic data comes in the form of
solid agar plate colonies. The pipeline takes care of spotting possible contaminations
in the plates and errors in the colony recognition, as well as picking the optimal
time piint for each condition. The actual phenotypic score is carried out by
the [EMAP matlab library](https://genomebiology.biomedcentral.com/articles/10.1186/gb-2006-7-7-r63),
which the user should run after the first steps of the pipeline.
Subsequent steps take care of normalizing the data as well as deriving FDR-corrected p-values
for each growth phenotype.

Note
----

The pipeline and scripts come with limited documentation and is intended to work for the EcoRef
screening only, even though some scripts might be useful for similar analysis.
Please do get in touch with the author (Marco Galardini, marco@ebi.ac.uk) if you need any guidance.

Usage
-----

Colony sizes/colony opacities files, as computed by [Iris](https://github.com/critichu/Iris)
are needed as inputs (provided in the batch5.tar.gz and batch6.tar.gz files).

The makefile contains the various bits of the pipeline:
* `make select` will scan the Iris files and pick the optimal timepoint for each condition and replica
* `make collect` will collect the Iris files corresponding to the selected timepoints
* `make pre-process` will remove artifacts generated by Iris and possible plate contaminations
* (here the user is expected to run [EMAP](https://genomebiology.biomedcentral.com/articles/10.1186/gb-2006-7-7-r63) on the results of the `make pre-process` step)
* `make post-process` will normalize the S-scores as computed by EMAP, as well as compute FDR-corrected p-value for each S-score
* `make deletion` will process the S-scores derived from a chemical genomics screening

Dependencies
------------

* python (2.7+ AND 3.3+), plus the following libraries:
    * pandas
    * numpy
    * scipy
    * fastcluster
    * statsmodels
    * networkx

Copyright
---------

Copyright (C) <2015> EMBL-European Bioinformatics Institute

This program is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License as
published by the Free Software Foundation, either version 3 of
the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

Neither the institution name nor the name screenings
can be used to endorse or promote products derived from
this software without prior written permission.
For written permission, please contact <marco@ebi.ac.uk>.

Products derived from this software may not be called screenings
nor may screenings appear in their names without prior written
permission of the developers. You should have received a copy
of the GNU General Public License along with this program.
If not, see <http://www.gnu.org/licenses/>.
