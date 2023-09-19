import React, {useEffect, useState} from 'react';
import List, {ActionDataInterface} from "../../components/List";
import {useNavigate, useSearchParams} from "react-router-dom";
import axios from "axios";
import toLower from "lodash/toLower";
import DeleteIcon from "@mui/icons-material/Delete";
import {useAppDispatch} from "../../app/hooks";
import {setModule} from "../../reducers/module";
import {modules} from "../../modules";
import {postData} from "../../utils/Requests";
import Loading from "../../components/Loading";
import AlertDialog from '../../components/AlertDialog'
import Dataset from '../../models/dataset';
import Box from "@mui/material/Box";
import Tabs from "@mui/material/Tabs";
import Tab from "@mui/material/Tab";
import TabPanel, {a11yProps} from "../../components/TabPanel";
import Grid from "@mui/material/Grid";
import ViewSyncList from "../SyncStatus/List";
import {parseInt} from "lodash";
import {ThemeButton} from "../../components/Elements/Buttons";

const DELETE_DATASET_URL = '/api/delete-dataset'

const COLUMNS = [
  'id',
  'dataset',
  'created_by',
  'type',
  'date',
  'sync_status',
  'permissions',
  'is_empty',
  'is_active'
]

export default function Dataset() {
  const pageName = 'Dataset'
  const datasetUrlList = '/api/dataset-group/list/'
  const [searchParams, setSearchParams] = useSearchParams()
  const [dataset, setDataset] = useState<Dataset[]>([])
  const [selectedDataset, setSelectedDataset] = useState<Dataset>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [confirmationOpen, setConfirmationOpen] = useState<boolean>(false)
  const [confirmationText, setConfirmationText] = useState<string>('')
  const [deleteButtonDisabled, setDeleteButtonDisabled] = useState<boolean>(false)
  const [tabSelected, setTabSelected] = useState(0)
  const dispatch = useAppDispatch()
  const navigate = useNavigate()
  const customColumnOptions = {
    'is_active': {
        filter: true,
        sort: true,
        display: true,
        customBodyRender: (value: any, tableMeta: any, updateValue: any) => {
          return value ? 'Active' : 'Deprecated'
        }
    },
    'sync_status': {
        filter: true,
        sort: true,
        display: true,
        customBodyRender: (value: any, tableMeta: any, updateValue: any) => {
          const onClick = (e: any) => {
            e.stopPropagation();
            navigate(`/admin_boundaries/dataset_entities?id=${tableMeta.rowData[0]}&tab=8`)
          }
          if (value != 'Synced') {
            return (
              <ThemeButton
                icon={null}
                title={'Out of Sync'}
                variant={'secondary'}
                onClick={onClick}
              />
            )
          }
          return 'Synced'
        }
    }
  }

  const customColumnHeaderRender = {
    'is_active': (columnMeta: any, handleToggleColumn: Function) => {
        return <span>Status</span>
    }
  }

  const fetchDataset = () => {
    setLoading(true)
    axios.get(datasetUrlList).then(
      response => {
        setLoading(false)
        setDataset(response.data.map((d: any)=>{
          let keys = Object.keys(d)
          for (const key of keys) {
            if (!(COLUMNS.includes(key))) {
              delete d[key]
            }
          }
          return d
        }))
      }
    )
  }

  useEffect(() => {
    let tab = searchParams.get('tab') ? parseInt(searchParams.get('tab')) : 0
    if (tab === 0) {
      fetchDataset()
    }
    setTabSelected(tab as unknown as number)
  }, [searchParams])

  useEffect(() => {
    if (tabSelected === 0) {
      fetchDataset()
    }
  }, [tabSelected])

  const actionDeleteButton: ActionDataInterface = {
    field: '',
    name: 'Delete',
    getName: (data: any) => {
        if (!data.permissions.includes('Own')) {
            return 'You are not owner of this dataset'
        } else if (!data.is_empty) {
          return 'Cannot remove non-empty dataset'
        }
        return 'Delete'
    },
    color: 'error',
    icon: <DeleteIcon />,
    isDisabled: (data: any) => {
      return !data.permissions.includes('Own') || !data.is_empty
    },
    onClick: (data: any) => {
      setSelectedDataset(data)
      setConfirmationText(
        `Are you sure you want to delete ${data.dataset}?`)
      setConfirmationOpen(true)
    }
  }

  const handleEditClick = (rowData: any) => {
    let moduleName = toLower(rowData[3]).replace(' ', '_')
    const datasetId = rowData[0]
    if (!moduleName) {
      moduleName = modules[0]
    }
    dispatch(setModule(moduleName))
    navigate(`/${moduleName}/dataset_entities?id=${datasetId}`)
  }

  const handleRowClick = (rowData: string[], rowMeta: { dataIndex: number, rowIndex: number }) => {
    handleEditClick(rowData)
  }

  const handleDeleteClick = () => {
    setDeleteButtonDisabled(true)
    postData(
      `${DELETE_DATASET_URL}/${selectedDataset.id}`, {}
    ).then(
      response => {
        setDeleteButtonDisabled(false)
        fetchDataset()
        setConfirmationOpen(false)
      }
    ).catch(error => {
      setDeleteButtonDisabled(false)
      alert('Error deleting dataset')
    })
  }

  const handleClose = () => {
    setConfirmationOpen(false)
  }

  return (
    <div className="AdminContentMain main-data-list">
      <AlertDialog open={confirmationOpen} alertClosed={handleClose}
          alertConfirmed={handleDeleteClick}
          alertLoading={deleteButtonDisabled}
          alertDialogTitle={'Delete dataset'}
          alertDialogDescription={confirmationText}
          confirmButtonText='Delete'
          confirmButtonProps={{color: 'error', autoFocus: true}}
      />
      {!loading ?
        <List
          pageName={pageName}
          listUrl={''}
          initData={dataset}
          selectionChanged={null}
          onRowClick={handleRowClick}
          actionData={[actionDeleteButton]}
          excludedColumns={['permissions', 'is_empty']}
          customOptions={customColumnOptions}
          customColumnHeaderRender={customColumnHeaderRender}
        /> : <Loading/>
      }
    </div>
  )
}
