# Copyright (c) Facebook, Inc. and its affiliates. All rights reserved.

import json
import os
import warnings
from os import path
from pathlib import Path

import torch
from pytorch3d.io import load_obj


SYNSET_DICT_DIR = Path(__file__).resolve().parent


class ShapeNetCore(torch.utils.data.Dataset):
    """
    This class loads ShapeNetCore from a given directory into a Dataset object.
    ShapeNetCore is a subset of the ShapeNet dataset and can be downloaded from
    https://www.shapenet.org/.
    """

    def __init__(self, data_dir, synsets=None, version: int = 1):
        """
        Store each object's synset id and models id from data_dir.
        Args:
            data_dir: Path to ShapeNetCore data.
            synsets: List of synset categories to load from ShapeNetCore in the form of
                synset offsets or labels. A combination of both is also accepted.
                When no category is specified, all categories in data_dir are loaded.
            version: (int) version of ShapeNetCore data in data_dir, 1 or 2.
                Default is set to be 1. Version 1 has 57 categories and verions 2 has 55
                categories.
                Note: version 1 has two categories 02858304(boat) and 02992529(cellphone)
                that are hyponyms of categories 04530566(watercraft) and 04401088(telephone)
                respectively. You can combine the categories manually if needed.
                Version 2 doesn't have 02858304(boat) or 02834778(bicycle) compared to
                version 1.

        """
        self.data_dir = data_dir
        if version not in [1, 2]:
            raise ValueError('Version number must be either 1 or 2.')
        self.model_dir = (
            'model.obj' if version == 1 else 'models/model_normalized.obj'
        )

        # Synset dictionary mapping synset offsets to corresponding labels.
        dict_file = 'shapenet_synset_dict_v%d.json' % version
        with open(path.join(SYNSET_DICT_DIR, dict_file), 'r') as read_dict:
            self.synset_dict = json.load(read_dict)
        # Inverse dicitonary mapping synset labels to corresponding offsets.
        synset_inv = {
            label: offset for offset, label in self.synset_dict.items()
        }

        # If categories are specified, check if each category is in the form of either
        # synset offset or synset label, and if the category exists in the given directory.
        if synsets is not None:
            # Set of categories to load in the form of synset offsets.
            synset_set = set()
            for synset in synsets:
                if (synset in self.synset_dict.keys()) and (
                    path.isdir(path.join(data_dir, synset))
                ):
                    synset_set.add(synset)
                elif (synset in synset_inv.keys()) and (
                    (path.isdir(path.join(data_dir, synset_inv[synset])))
                ):
                    synset_set.add(synset_inv[synset])
                else:
                    msg = """Synset category %s either not part of ShapeNetCore dataset
                         or cannot be found in %s.""" % (
                        synset,
                        data_dir,
                    )
                    warnings.warn(msg)
        # If no category is given, load every category in the given directory.
        else:
            synset_set = {
                synset
                for synset in os.listdir(data_dir)
                if path.isdir(path.join(data_dir, synset))
            }
            for synset in synset_set:
                if synset not in self.synset_dict.keys():
                    msg = """Synset category %s(%s) is part of ShapeNetCore ver.%s
                        but not found in %s.""" % (
                        synset,
                        self.synset_dict[synset],
                        version,
                        data_dir,
                    )
                    warnings.warn(msg)

        # Extract model_id of each object from directory names.
        # Each grandchildren directory of data_dir contains an object, and the name
        # of the directory is the object's model_id.
        self.synset_ids = []
        self.model_ids = []
        for synset in synset_set:
            for model in os.listdir(path.join(data_dir, synset)):
                if not path.exists(
                    path.join(data_dir, synset, model, self.model_dir)
                ):
                    msg = """ Object file not found in the model directory %s
                        under synset directory %s.""" % (
                        model,
                        synset,
                    )
                    warnings.warn(msg)
                else:
                    self.synset_ids.append(synset)
                    self.model_ids.append(model)

    def __len__(self):
        """
        Return number of total models in shapenet core.
        """
        return len(self.model_ids)

    def __getitem__(self, idx):
        """
        Read a model by the given index.
        Returns:
            dictionary with following keys:
            - verts: FloatTensor of shape (V, 3).
            - faces: LongTensor of shape (F, 3) which indexes into the verts tensor.
            - synset_id (str): synset id
            - model_id (str): model id
            - label (str): synset label.
        """
        model = {}
        model['synset_id'] = self.synset_ids[idx]
        model['model_id'] = self.model_ids[idx]
        model_path = path.join(
            self.data_dir, model['synset_id'], model['model_id'], self.model_dir
        )
        model['verts'], faces, _ = load_obj(model_path)
        model['faces'] = faces.verts_idx
        model['label'] = self.synset_dict[model['synset_id']]
        return model
