import React, { useState } from "react";
import DatasetDetail from "../views/Dataset/DatasetDetail";
import { DatasetTabElementInterface } from "../models/dataset"
import DatasetStyle from "../views/Dataset/Configurations/DatasetStyles";
import DatasetPermission from "../views/Dataset/Configurations/DatasetPermission";
import DatasetGeneral from "./Configurations/DatasetGeneral";
import DatasetTilingConfig from "../views/Dataset/Configurations/DatasetTilingConfig";
import DatasetAdminLevelNames from "./Configurations/DatasetAdminLevelNames";
import DatasetEntities from "../views/Dataset/DatasetEntities";


export default function DatasetDetailWrapper() {
    const [tabs, setTabs] = useState<DatasetTabElementInterface[]>([
        {
            title: 'PREVIEW',
            element: DatasetEntities,
            permissions: ['Read']
        },
        {
            title: 'GENERAL',
            element: DatasetGeneral,
            permissions: ['Manage']
        },
        {
            title: 'PERMISSION',
            element: DatasetPermission,
            permissions: ['Manage']
        },
        {
            title: 'ADMIN LEVEL NAMES',
            element: DatasetAdminLevelNames,
            permissions: ['Manage']
        },
        {
            title: 'STYLE',
            element: DatasetStyle,
            permissions: ['Manage']
        },
        {
            title: 'TILING CONFIG',
            element: DatasetTilingConfig,
            permissions: ['Manage']
        }
    ])
    return (
        <DatasetDetail moduleName={'admin_boundaries'} tabs={tabs} />
    )
}