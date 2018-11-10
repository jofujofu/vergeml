from vergeml.command import command, CommandPlugin
from vergeml.option import option

import os.path
import csv
from vergeml.utils import VergeMLError
import numpy as np

@command('roc', descr="Plot a ROC curve.")
@option('@AI', type='AI')
@option('class', type='Optional[str]', descr="The class to plot.")
class ROCPlot(CommandPlugin):

    def __call__(self, args, env):
        # Plotting a ROC curve needs the model to follow the convention
        # - labels.txt in checkpoints
        # - predictions.csv in stats

        # TODO hide deprecation error when importing
        # maybe configure matplotlib as a lib?
        from sklearn.metrics import roc_curve, auc
        import matplotlib.pyplot as plt
        from itertools import cycle
        from scipy import interp

        lw = 2
       
        # Get labels
        path = os.path.join(env.checkpoints_dir(), "labels.txt")

        if not os.path.exists(path):
            raise VergeMLError("Can't plot ROC chart - not supported by model.")
        
        with open(path) as labelsfile:
            labels = labelsfile.read().strip().splitlines()
            nclasses = len(labels)
        
        if args['class'] is not None and args['class'] not in labels:
            raise VergeMLError("Unknown class: " + args['class'])

        # Get predictions
        path = os.path.join(env.stats_dir(), "predictions.csv")

        if not os.path.exists(path):
            raise VergeMLError("Can't plot ROC chart - not supported by model.")

        with open(path, newline='') as csvfile:
            y_score = []
            y_test = []
            csv_reader = csv.reader(csvfile, dialect="excel")
            for row in csv_reader:
                assert len(row) == nclasses * 2
                y_score.append(list(map(float, row[:nclasses])))
                y_test.append(list(map(float, row[nclasses:])))
            
            y_score = np.array(y_score)
            y_test = np.array(y_test)

        # From:
        # https://scikit-learn.org/stable/auto_examples/model_selection/plot_roc.html

        # Compute ROC curve and ROC area for each class
        fpr = dict()
        tpr = dict()
        roc_auc = dict()
        for i in range(nclasses):
            fpr[i], tpr[i], _ = roc_curve(y_test[:, i], y_score[:, i])
            roc_auc[i] = auc(fpr[i], tpr[i])

        # Compute micro-average ROC curve and ROC area
        fpr["micro"], tpr["micro"], _ = roc_curve(y_test.ravel(), y_score.ravel())
        roc_auc["micro"] = auc(fpr["micro"], tpr["micro"])

        if args['class']:
            ix = labels.index(args['class'])
            plt.figure()
            plt.plot(fpr[ix], tpr[ix], color='darkorange',
                    lw=lw, label='ROC curve of class {0} (area = {1:0.2f})'.format(args['class'], roc_auc[ix]))
            plt.plot([0, 1], [0, 1], color='navy', lw=lw, linestyle='--')
            plt.xlim([0.0, 1.0])
            plt.ylim([0.0, 1.05])
            plt.xlabel('False Positive Rate')
            plt.ylabel('True Positive Rate')
            plt.title('ROC curve for @' + args['@AI'])
            plt.legend(loc="lower right")
            plt.show()
        else:

            # Compute macro-average ROC curve and ROC area

            # First aggregate all false positive rates
            all_fpr = np.unique(np.concatenate([fpr[i] for i in range(nclasses)]))

            # Then interpolate all ROC curves at this points
            mean_tpr = np.zeros_like(all_fpr)
            for i in range(nclasses):
                mean_tpr += interp(all_fpr, fpr[i], tpr[i])

            # Finally average it and compute AUC
            mean_tpr /= nclasses

            fpr["macro"] = all_fpr
            tpr["macro"] = mean_tpr
            roc_auc["macro"] = auc(fpr["macro"], tpr["macro"])

            # Plot all ROC curves
            plt.figure()
            plt.plot(fpr["micro"], tpr["micro"],
                    label='micro-average ROC curve (area = {0:0.2f})'
                        ''.format(roc_auc["micro"]),
                    color='deeppink', linestyle=':', linewidth=4)

            plt.plot(fpr["macro"], tpr["macro"],
                    label='macro-average ROC curve (area = {0:0.2f})'
                        ''.format(roc_auc["macro"]),
                    color='navy', linestyle=':', linewidth=4)

            colors = cycle(['aqua', 'darkorange', 'cornflowerblue', 'maroon', 'indigo'])
            for i, color in zip(range(nclasses), colors):
                plt.plot(fpr[i], tpr[i], color=color, lw=lw,
                        label='ROC curve of class {0} (area = {1:0.2f})'
                        ''.format(labels[i], roc_auc[i]))

            plt.plot([0, 1], [0, 1], 'k--', lw=lw)
            plt.xlim([0.0, 1.0])
            plt.ylim([0.0, 1.05])
            plt.xlabel('False Positive Rate')
            plt.ylabel('True Positive Rate')
            plt.title('ROC curve for @' + args['@AI'])
            plt.legend(loc="lower right")
            plt.show()
        