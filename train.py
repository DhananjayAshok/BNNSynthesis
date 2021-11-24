import torch
import mnist as m_train
from adults import AdultsDataset
from toy_data import IdentityDataset, AffineDataset, PolynomialDataset, FormulaDataset, ThresholdDataset
from model import *


def get_loaders(key):
    if key == "mnist":
        return m_train.loaders()
    elif key == "identity":
        return IdentityDataset.loaders()
    elif key == "affine":
        return AffineDataset.loaders()
    elif key == "polynomial":
        return PolynomialDataset.loaders()
    elif key == "formula":
        return FormulaDataset.loaders()
    elif key == "threshold":
        return ThresholdDataset.loaders()
    elif key == "adults":
        return AdultsDataset.loaders()


def get_model(key):
    if key == "mnist":
        return m_train.model()
    elif key == "identity":
        return IdentityDataset.model()
    elif key == "affine":
        return AffineDataset.model()
    elif key == "polynomial":
        return PolynomialDataset.model()
    elif key == "formula":
        return FormulaDataset.model()
    elif key == "threshold":
        return ThresholdDataset.model()
    elif key == "adults":
        return AdultsDataset.model()


def get_metric(key):
    if key == "mnist":
        return m_train.metric()
    elif key == "identity":
        return IdentityDataset.metric()
    elif key == "affine":
        return AffineDataset.metric()
    elif key == "polynomial":
        return PolynomialDataset.metric()
    elif key == "formula":
        return FormulaDataset.metric()
    elif key == "threshold":
        return ThresholdDataset.metric()
    elif key == "adults":
        return AdultsDataset.metric()


epochs = 2
batch_limit = 1
lr = 0.01
key = "mnist"

train_loader, test_loader = get_loaders(key)
model = get_model(key)
metric = get_metric(key)
optimizer = torch.optim.SGD(model.parameters(), lr=lr)
train_losses, train_counter, test_losses = [], [], []
test_counter = [i*len(train_loader.dataset) for i in range(epochs + 1)]
log_interval = 1500
l1_metric = nn.L1Loss()


def train(epoch):
    model.train()
    for batch_idx, (data, target) in enumerate(train_loader):
        optimizer.zero_grad()
        output = model(data)
        loss = metric(output, target)
        loss.backward()
        optimizer.step()
        if batch_idx % log_interval == 0:
            print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                epoch, batch_idx * len(data), len(train_loader.dataset), 100. * batch_idx / len(train_loader),
                loss.item()))
            train_losses.append(loss.item())
            train_counter.append((batch_idx*64) + ((epoch-1)*len(train_loader.dataset)))
        if batch_limit is not None and batch_idx >= batch_limit:
            print(f"Early exit reached batch limit")
            break


def milp_train():
    for batch_idx, (data, target) in enumerate(train_loader):
        X = model.forward_till_dense(data)
        output = model(data)
        # target = encoder(target)
        # print(output.shape, target.shape)
        beforeloss = metric(output, target)
        beforeL1 = None
        afterL1 = None
        model.milp_model.initialize_mlp_model(w_range=0.1)
        if model.milp_model.classification:
            beforeAcc = torch.sum(torch.argmax(output, dim=1) == target)/len(target)
            min_accuracy = beforeAcc + 0.05
            model.milp_model.build_mlp_model(X, target, min_acc=min_accuracy)
        else:
            beforeL1 = l1_metric(output, target)
            l1 = torch.abs(output - target)
            l1= l1.mean()
            #l1 = None
            model.milp_model.build_mlp_model(X, target, max_loss=l1)
        #model.milp_model.report_mlp(verbose=False, constraint_loop_verbose=True)
        model.milp_model.solve_and_assign()
        #model.milp_model.report_mlp(verbose=False, constraint_loop_verbose=True)
        output = model(data)
        loss = metric(output, target)
        if model.milp_model.classification:
            afterAcc = torch.sum(torch.argmax(output, dim=1) == target)/len(target)
        else:
            afterL1 = l1_metric(output, target)
        print(f"Before loss was {beforeloss.item()}")
        print(f"Now loss is {loss.item()}")
        if model.milp_model.classification:
            print(f"Before Accuracy was {beforeAcc*100}%")
            print(f"Now Accuracy is {afterAcc*100}%")
        else:
            print(f"Before L1 was {beforeL1.item()}")
            print(f"Now L1 is {afterL1.item()}")
        break


def evaluate():
    model.eval()
    val_losses = []
    for batch_idx, (data, target) in enumerate(test_loader):
        output = model(data)
        loss = metric(output, target)
        val_losses.append(loss.item())
    val_losses = torch.Tensor(val_losses)
    print(f"Mean Loss: {torch.mean(val_losses)} Variance Loss: {torch.std(val_losses)}")


def acc_evaluate():
    model.eval()
    val_losses = []
    for batch_idx, (data, target) in enumerate(test_loader):
        output = model(data)
        predictions = torch.argmax(output, axis=1)
        acc = (torch.sum(predictions == target)*100)/len(target)
        val_losses.append(acc.item())
    val_losses = torch.Tensor(val_losses)
    print(f"Mean Accuracy: {torch.mean(val_losses)} Variance Accuracy: {torch.std(val_losses)}")


for epoch in range(1, epochs + 1):
    train(epoch)

evaluate()

acc_evaluate()

milp_train()

acc_evaluate()

for epoch in range(1, epochs + 1):
    pass
    train(epoch)

evaluate()

acc_evaluate()
