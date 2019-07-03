import os

import schnetpack as spk
import torch
from torch.optim import Adam


__all__ = ["get_trainer", "simple_loss_fn", "tradeoff_loff_fn"]


def get_trainer(args, model, train_loader, val_loader, metrics, loss_fn=None):
    # setup hook and logging
    hooks = [spk.train.MaxEpochHook(args.max_epochs)]

    # filter for trainable parameters (https://github.com/pytorch/pytorch/issues/679)
    trainable_params = filter(lambda p: p.requires_grad, model.parameters())
    optimizer = Adam(trainable_params, lr=args.lr)

    schedule = spk.train.ReduceLROnPlateauHook(
        optimizer=optimizer,
        patience=args.lr_patience,
        factor=args.lr_decay,
        min_lr=args.lr_min,
        window_length=1,
        stop_after_min=True,
    )
    hooks.append(schedule)

    if args.logger == "csv":
        logger = spk.train.CSVHook(
            os.path.join(args.modelpath, "log"),
            metrics,
            every_n_epochs=args.log_every_n_epochs,
        )
        hooks.append(logger)
    elif args.logger == "tensorboard":
        logger = spk.train.TensorboardHook(
            os.path.join(args.modelpath, "log"),
            metrics,
            every_n_epochs=args.log_every_n_epochs,
        )
        hooks.append(logger)

    if loss_fn is None:
        loss_fn = simple_loss_fn(args)

    trainer = spk.train.Trainer(
        args.modelpath,
        model,
        loss_fn,
        optimizer,
        train_loader,
        val_loader,
        checkpoint_interval=1,
        hooks=hooks,
    )
    return trainer


def simple_loss_fn(args):
    def loss(batch, result):
        diff = batch[args.property] - result[args.property]
        diff = diff ** 2
        err_sq = torch.mean(diff)
        return err_sq

    return loss


def tradeoff_loff_fn(args, derivative):
    def loss(batch, result):
        diff = batch[args.property] - result[args.property]
        diff = diff ** 2

        der_diff = batch[derivative] - result[derivative]
        der_diff = der_diff ** 2

        err_sq = args.rho * torch.mean(diff.view(-1)) + (1 - args.rho) * torch.mean(
            der_diff.view(-1)
        )
        return err_sq

    return loss
