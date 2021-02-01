def calculate_weight(constant, index):
    return constant ** index

def base_curve(accuracy, curve_data):
    # https://www.desmos.com/calculator/bkyq4lsq2l
    # baseline: z
    # cutoff: w
    # exponential: v

    # apply default values
    defaults = {
        'baseline': 0.78,
        'cutoff': 0.5,
        'exponential': 2.5,
    }
    defaults.update(curve_data)
    curve_data = defaults

    baseline = curve_data['baseline'] * 100
    cutoff = curve_data['cutoff']
    exponential = curve_data['exponential']
    if accuracy < baseline:
        return accuracy / 100 * cutoff
    else:
        return accuracy / 100 * cutoff + (1 - cutoff) * ((accuracy - baseline)/(100 - baseline)) ** exponential

curves = {
    'basic': base_curve,
}

def cr_score_curve(accuracy, curve_data):
    return curves[curve_data['type']](accuracy, curve_data)

def calculate_cr(accuracy, difficulty, curve_data):
    return difficulty * 50 * cr_score_curve(accuracy, curve_data)

def cr_accumulation_curve(index):
    accumulation_constant = 0.94
    if index > 50:
        return 0
    else:
        return accumulation_constant ** index
