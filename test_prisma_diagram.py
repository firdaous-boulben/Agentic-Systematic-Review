from tools.prisma_diagram import generate_prisma_diagram

sample_data = {
    "records_identified": 50,
    "duplicates_removed": 1,
    "records_after_duplicates_removed": 49,
    "records_screened": 5,
    "records_not_yet_screened": 44,
    "records_excluded": 2,
    "records_included_after_screening": 2,
    "records_uncertain": 1
}

generate_prisma_diagram(sample_data)
