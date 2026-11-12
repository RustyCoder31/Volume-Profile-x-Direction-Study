from model.volume_profile import ProfileWalker


def profile_shape(vp_df):
    """Determine the shape of the volume profile based on the distribution of volume across price levels."""

    total_volume = vp_df.sum()
    mid_point = (vp_df.index.max() + vp_df.index.min()) / 2
    # A row exactly on the midpoint belongs to neither half. It is left out of the
    # upper half but kept in the total, so it counts toward the lower side. That
    # makes P need a clear upper majority. One row in about a thousand, so tiny.
    upper_half = vp_df[vp_df.index > mid_point]
    upper_half_volume = upper_half.sum()
    upper_half_percentage = upper_half_volume / total_volume * 100

    return shape_from_pct(upper_half_percentage), upper_half_percentage


def shape_from_pct(upper_half_percentage):
    """The 60 / 40 rule: above 60 percent of volume in the upper half is P, below 40 is b, else D."""
    if upper_half_percentage > 60:
        return "P-shaped"
    if upper_half_percentage < 40:
        return "b-shaped"
    return "D-shaped"


def shape_labels(day_df, last, walker=None):
    """labels[j] is the shape label at bar j (profile of bars 0 to j-1). Bar 0 has no profile.
    Pass a ProfileWalker to share one running profile with other code; otherwise one is made."""
    walker = walker or ProfileWalker(day_df)
    labels = [None]
    for j in range(1, last + 1):
        labels.append(shape_from_pct(walker.at(j).upper_pct))
    return labels


def shape_age(labels, i):
    """How many bars the shape label at bar i has stayed the same, counting back from i-1."""
    age = 0
    for j in range(i - 1, 0, -1):
        if labels[j] != labels[i]:
            break
        age += 1
    return age
