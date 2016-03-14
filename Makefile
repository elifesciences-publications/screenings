BATCH = batch6
IRIS = iris_0.9.4.71

MINSIZE = 1900
MAXSIZE = 1700
COLOR = 

PLATE = 8
PLATEFILE = $(CURDIR)/plates.tsv
BATCHDIR = ../../datasets/screens/BATCH6/

SRCDIR = $(CURDIR)/src
NOTEBOOKSDIR = $(CURDIR)/notebooks

RAWDIR = $(CURDIR)/$(BATCH).raw
ifeq ($(COLOR),--color)
  RAWDIR=$(CURDIR)/$(BATCH).raw.color
endif
$(RAWDIR):
	mkdir -p $(RAWDIR)

FIXEDDIR = $(CURDIR)/fixed/$(BATCH)
ifeq ($(COLOR),--color)
  FIXEDDIR=$(CURDIR)/fixed.color/$(BATCH).color
endif
$(FIXEDDIR):
	mkdir -p $(FIXEDDIR)

TIMEPOINTS = $(CURDIR)/$(BATCH).tpoints.tsv
NAMECONVERSION = $(CURDIR)/$(BATCH).file_conversion.txt

MISSING = $(CURDIR)/$(BATCH).missing.txt
ADDITIONALMISSING = $(CURDIR)/$(BATCH).additional_missing.txt

SEQUENCED = $(CURDIR)/sequenced.txt

EMAP = $(CURDIR)/fileForCluster3.txt
RENAMED = $(CURDIR)/fileForCluster3.renamed.txt
RESTRICTED = $(CURDIR)/fileForCluster3.restricted.txt
RESCALED = $(CURDIR)/fileForCluster3.rescaled.txt
MERGED = $(CURDIR)/emap.matrix.txt
FDR = $(CURDIR)/emap.fdr.txt

# Name conversion
CONVERSION = $(CURDIR)/conditions.csv

# External data
ROARY = $(CURDIR)/gene_presence_absence.csv
SNPS = $(CURDIR)/SNPs_matrix.tsv
SNPSDEL = $(CURDIR)/SNPs_del_matrix.tsv
SNPSFUNCTIONAL = $(CURDIR)/SNPs_functional_matrix.tsv

# External data: deletion screen
DELDIR = $(CURDIR)/deletion_screen
DELIN = $(DELDIR)/Cleaner_NormScores_joinedConds.txt
DEL = $(CURDIR)/deletion.matrix.txt
DELFDR = $(CURDIR)/deletion.fdr.txt
DELGENES = $(CURDIR)/deletion.genes.txt
DELALLIN = $(DELDIR)/NTB456.txt
DELALL = $(CURDIR)/deletion.all.matrix.txt
DELALLFDR = $(CURDIR)/deletion.all.fdr.txt
DELALLGENES = $(CURDIR)/deletion.all.genes.txt
DELALLCLUSTERS = $(CURDIR)/deletion.all.clusters.txt

# Merging conditions
SHARED = $(DELDIR)/shared_conditions.txt
MERGEDDIR = $(CURDIR)/merged
$(MERGEDDIR):
	mkdir -p $(MERGEDDIR)

########################
## Select time points ##
########################

ifeq ($(COLOR),--color)
  TIMEPOINTS=$(CURDIR)/$(BATCH).tpoints.color.tsv
endif

ifeq ($(BATCH),batch5)
  SELECT1=find $(BATCHDIR) -name '*.iris' | grep $(IRIS) | grep -v Keio | $(SRCDIR)/get_time_points_$(BATCH) - --size-min $(MINSIZE) --size-max $(MAXSIZE) $(COLOR) > $(TIMEPOINTS)
  SELECT2=echo "nothing to be done here"
  JOIN=echo "nothing to be done here"
else
  SELECT1=find $(BATCHDIR) -name '*.iris' | grep $(IRIS) | $(SRCDIR)/get_time_points_$(BATCH) - --exclude 10_A --exclude 10_B --exclude 10_C --size-min 1900 --size-max 1700 $(COLOR) > $(TIMEPOINTS).89
  SELECT2=find $(BATCHDIR) -name '*.iris' | grep $(IRIS) | $(SRCDIR)/get_time_points_$(BATCH) - --exclude 9_A --exclude 9_B --exclude 9_C --exclude 8_A --exclude 8_B --exclude 8_C --size-min 1300 --size-max 2300 $(COLOR) > $(TIMEPOINTS).10
  JOIN=$(SRCDIR)/fix_batch6 $(TIMEPOINTS).89 $(TIMEPOINTS).10 > $(TIMEPOINTS)
endif

$(TIMEPOINTS): $(BATCHDIR)
	$(SELECT1)
	$(SELECT2)
	$(JOIN)

#############
## Collect ##
#############

ifeq ($(COLOR),--color)
  NAMECONVERSION=$(CURDIR)/$(BATCH).file_conversion.color.txt
endif

$(NAMECONVERSION): $(TIMEPOINTS) $(RAWDIR)
	$(SRCDIR)/collect_iris_$(BATCH) $(TIMEPOINTS) $(BATCHDIR) $(RAWDIR) $(PLATE) $(IRIS) > $(NAMECONVERSION)

####################
## Pre-processing ##
####################

$(MISSING): $(NAMECONVERSION) $(PLATEFILE)
	$(SRCDIR)/missing_colonies --size 0 --percentile 0.66 $(RAWDIR) $(PLATEFILE) > $(MISSING)
	cat $(ADDITIONALMISSING) >> $(MISSING)

RAWS = $(wildcard $(RAWDIR)/*.iris)
FIXEDS = $(foreach RAW,$(RAWS),$(addprefix $(FIXEDDIR)/,$(addsuffix .iris,$(basename $(notdir $(RAW))))))

$(FIXEDDIR)/%.iris: $(RAWDIR)/%.iris $(MISSING) $(PLATEFILE) $(FIXEDDIR)
	$(SRCDIR)/fix_iris --circularity1 0.5 --size 1000 --circularity2 0.3 --ignore $(MISSING) --variance-size 0.9 --variance-circularity 0.95 $< $(PLATEFILE) $(FIXEDDIR) 

######################
## Post-processing  ##
######################

$(RENAMED): $(EMAP)
	$(SRCDIR)/rename_matrix $(EMAP) $(CONVERSION) $(RENAMED)

$(RESTRICTED): $(RENAMED) $(SEQUENCED)
	$(SRCDIR)/remove_strains $(RENAMED) $(SEQUENCED) $(RESTRICTED)

$(RESCALED): $(RESTRICTED)
	$(SRCDIR)/rescale_sscores $(RESTRICTED) > $(RESCALED)

$(MERGED): $(RESCALED)
	$(SRCDIR)/merge_columns $(RESCALED) > $(MERGED)

$(FDR): $(MERGED)
	$(SRCDIR)/fdr_matrix $(MERGED) $(FDR)

######################################
## Deletion screen post-processing  ##
######################################

# DELOPTIONS = --threshold -12 --absolute
DELOPTIONS =

$(DEL): $(DELIN)
	$(SRCDIR)/remove_duplicates $< $@

$(DELFDR): $(DEL)
	$(SRCDIR)/fdr_matrix $(DEL) $(DELFDR) --index genes

$(DELGENES): $(DEL) $(DELFDR)
	$(SRCDIR)/important_genes $(DEL) $(DELFDR) --index1 genes --index2 genes --filter Deletion $(DELOPTIONS) > $(DELGENES)

$(DELALL): $(DELALLIN)
	$(SRCDIR)/remove_duplicates $< $@

$(DELALLFDR): $(DELALL)
	$(SRCDIR)/fdr_matrix $(DELALL) $(DELALLFDR) --index genes

$(DELALLGENES): $(DELALL) $(DELALLFDR)
	$(SRCDIR)/important_genes $(DELALL) $(DELALLFDR) --index1 genes --index2 genes --no-filter $(DELOPTIONS) > $(DELALLGENES)

##############################################
## Merge conditions using chemical genomics ##
##############################################

$(DELALLCLUSTERS): $(DELALL)
	$(SRCDIR)/do_correlation $(DELALL) deletion.all.correlation.txt --filter --pearson --columns
	$(SRCDIR)/get_hclusters deletion.all.correlation.txt deletion.all.linkage.txt deletion.all.dendrogram.txt --iterations 100 --score 0.2 --distance > $(DELALLCLUSTERS)

$(CURDIR)/merging.done: $(DELALLCLUSTERS) $(SHARED) $(MERGEDDIR) $(MERGED)
	$(SRCDIR)/combine_conditions $(DELALLCLUSTERS) $(SHARED) $(MERGED) $(MERGEDDIR) > $@

########################
## Reports generation ##
########################

NPHENOTYPES = $(NOTEBOOKSDIR)/phenotypes.ipynb
RPHENOTYPES = $(NOTEBOOKSDIR)/phenotypes.html
$(RPHENOTYPES): $(NPHENOTYPES) $(RESCALED) $(FDR)
	runipy -o $(NPHENOTYPES) && \
	cd $(NOTEBOOKSDIR) && ipython nbconvert --to=html $(notdir $(NPHENOTYPES)) --template html.tpl && cd $(CURDIR) && \
	git add $(NPHENOTYPES) && \
	git commit -m "Updated phenotypes report" && \
	git push

NGENOTYPES = $(NOTEBOOKSDIR)/phenotypes_genetics.ipynb
RGENOTYPES = $(NOTEBOOKSDIR)/phenotypes_genetics.html
$(RGENOTYPES): $(NGENOTYPES) $(RESCALED) $(FDR) $(ROARY) $(SNPS) $(SNPSDEL) $(SNPSFUNCTIONAL)
	runipy -o $(NGENOTYPES) && \
	cd $(NOTEBOOKSDIR) && ipython nbconvert --to=html $(notdir $(NGENOTYPES)) --template html.tpl && cd $(CURDIR) && \
	git add $(NGENOTYPES) && \
	git commit -m "Updated phenotypes/genotypes report" && \
	git push

select: $(TIMEPOINTS)
collect: $(NAMECONVERSION)
pre-process: $(FIXEDS)
post-process: $(RESCALED) $(FDR)
deletion: $(DEL) $(DELFDR) $(DELGENES) $(DELALL) $(DELALLFDR) $(DELALLGENES)
clusters: $(DELALLCLUSTERS) $(CURDIR)/merging.done
reports: $(RPHENOTYPES) $(RGENOTYPES)

.PHONY: select collect pre-process post-process deletion clusters reports
