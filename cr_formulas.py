def calculate_weight(constant, index):
    return constant ** index

def cr_score_curve(accuracy):
    baseline = 78
    if accuracy < baseline:
        return accuracy / 100 * 0.5
    else:
        return accuracy / 100 * 0.5 + 0.5 * ((accuracy - baseline)/(100 - baseline))**2.5

def calculate_cr(accuracy, difficulty):
    return difficulty * 50 * cr_score_curve(accuracy)

def cr_accumulation_curve(index):
    accumulation_constant = 0.94
    if index > 50:
        return 0
    else:
        return accumulation_constant ** index
