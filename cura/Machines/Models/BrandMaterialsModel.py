# Copyright (c) 2018 Ultimaker B.V.
# Cura is released under the terms of the LGPLv3 or higher.

from PyQt5.QtCore import Qt, pyqtSignal, pyqtProperty

from UM.Qt.ListModel import ListModel

from .BaseMaterialsModel import BaseMaterialsModel


class MaterialsModelGroupedByType(ListModel):
    NameRole = Qt.UserRole + 1
    ColorsRole = Qt.UserRole + 2

    def __init__(self, parent = None):
        super().__init__(parent)

        self.addRoleName(self.NameRole, "name")
        self.addRoleName(self.ColorsRole, "colors")


## Brand --> Material Type -> list of materials
class BrandMaterialsModel(ListModel):
    NameRole = Qt.UserRole + 1
    MaterialsRole = Qt.UserRole + 2

    extruderPositionChanged = pyqtSignal()

    def __init__(self, parent = None):
        super().__init__(parent)

        self.addRoleName(self.NameRole, "name")
        self.addRoleName(self.MaterialsRole, "materials")

        self._extruder_position = 0

        from cura.CuraApplication import CuraApplication
        self._machine_manager = CuraApplication.getInstance().getMachineManager()
        self._extruder_manager = CuraApplication.getInstance().getExtruderManager()
        self._material_manager = CuraApplication.getInstance().getMaterialManager()

        self._machine_manager.globalContainerChanged.connect(self._update)
        self._extruder_manager.activeExtruderChanged.connect(self._update)
        self._material_manager.materialsUpdated.connect(self._update)

        self._update()

    def setExtruderPosition(self, position: int):
        if self._extruder_position != position:
            self._extruder_position = position
            self.extruderPositionChanged.emit()

    @pyqtProperty(int, fset = setExtruderPosition, notify = extruderPositionChanged)
    def extruderPosition(self) -> int:
        return self._extruder_position

    def _update(self):
        global_stack = self._machine_manager.activeMachine
        if global_stack is None:
            self.setItems([])
            return
        extruder_stack = global_stack.extruders[str(self._extruder_position)]

        result_dict = self._material_manager.getAvailableMaterialsForMachineExtruder(global_stack, extruder_stack)
        if result_dict is None:
            self.setItems([])
            return

        brand_item_list = []
        brand_group_dict = {}
        for root_material_id, container_node in result_dict.items():
            metadata = container_node.metadata
            brand = metadata["brand"]
            # Only add results for generic materials
            if brand.lower() == "generic":
                continue

            if brand not in brand_group_dict:
                brand_group_dict[brand] = {}

            material_type = metadata["material"]
            if material_type not in brand_group_dict[brand]:
                brand_group_dict[brand][material_type] = []

            item = {"root_material_id": root_material_id,
                    "id": metadata["id"],
                    "name": metadata["name"],
                    "brand": metadata["brand"],
                    "material": metadata["material"],
                    "color_name": metadata["color_name"],
                    "container_node": container_node
                    }
            brand_group_dict[brand][material_type].append(item)

        for brand, material_dict in brand_group_dict.items():
            brand_item = {"name": brand,
                          "materials": MaterialsModelGroupedByType(self)}

            material_type_item_list = []
            for material_type, material_list in material_dict.items():
                material_type_item = {"name": material_type,
                                      "colors": BaseMaterialsModel(self)}
                material_type_item["colors"].clear()
                material_type_item["colors"].setItems(material_list)

                material_type_item_list.append(material_type_item)

            brand_item["materials"].setItems(material_type_item_list)

            brand_item_list.append(brand_item)

        self.setItems(brand_item_list)

