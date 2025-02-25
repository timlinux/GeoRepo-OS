import React, {useEffect, useState} from "react";
import clsx from 'clsx';
import List from "../../components/List";
import '../../styles/Step3.scss';
import axios from "axios";
import {useNavigate, useSearchParams} from "react-router-dom";
import Modal from '@mui/material/Modal';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import { DataGrid, GridColDef, GridColumnGroupingModel, GridColumnHeaderParams, GridCellParams } from '@mui/x-data-grid';
import CircularProgress from '@mui/material/CircularProgress';
import {postData} from "../../utils/Requests";
import {useAppDispatch} from "../../app/hooks";
import {setPollInterval, FETCH_INTERVAL_JOB} from "../../reducers/notificationPoll";
import {ReviewListRoute} from "../../views/routes";
import Scrollable from "../../components/Scrollable";
import Step4OverlapsError from './Step4OverlapsError'
import ColumnHeaderIcon from '../../components/ColumnHeaderIcon'
import { WizardStepInterface } from "../../models/upload";
import {utcToLocalDateTimeString} from '../../utils/Helpers';

const URL = '/api/entity-upload-status-list/'
const READY_TO_REVIEW_URL = '/api/ready-to-review/'


const columnRenderHeader = (field: string) => {
  if (field in COLUMN_DESCRIPTION) {
    return <ColumnHeaderIcon title={field} tooltipTitle={field}
      tooltipDescription={<p>{COLUMN_DESCRIPTION[field]}</p>}
    />
  }
  return <span>{field}</span>
}

const warningErrorTypes = [
  "Self Intersects",
  "Self Contacts",
  "Duplicate Nodes",
  "Gaps",
  "Upgraded Privacy Level"
]

const blockingErrorTypes = [
  "Polygon with less than 4 nodes",
  "Duplicated Geometries",
  "Feature within other features",
  "Overlaps",
  "Not Within Parent",
  "Parent Code Missing",
  "Default Code Missing",
  "Default Name Missing",
  "Duplicated Codes",
  "Invalid Privacy Level",
  "Privacy Level Missing",
  "Parent Missing"
]


const getCellClassName = (params: GridCellParams<any, any>) => {
  if (params.value == null || params.value == 0) {
    return ''
  }
  let _is_warning_col = warningErrorTypes.includes(params.field)
  return clsx('error-summary', {
    warning: params.value > 0 && _is_warning_col,
    error: params.value > 0&& !_is_warning_col,
  })
}

const columns: GridColDef[] = [
  { field: 'Level', sortable: false, filterable: false, disableColumnMenu: true },
  { field: 'Entity', width: 150, sortable: false, filterable: false, disableColumnMenu: true },
  { field: 'Self Intersects', width: 150, sortable: false, filterable: false, disableColumnMenu: true, renderHeader: (params: GridColumnHeaderParams) => columnRenderHeader(params.field), cellClassName: getCellClassName },
  // hide self contacts
  // { field: 'Self Contacts', sortable: false, filterable: false, disableColumnMenu: true },
  { field: 'Duplicate Nodes', sortable: false, filterable: false, disableColumnMenu: true, cellClassName: getCellClassName },
  { field: 'Polygon with less than 4 nodes', width: 150, sortable: false, filterable: false, disableColumnMenu: true },
  { field: 'Overlaps', width: 120, sortable: false, filterable: false, disableColumnMenu: true, renderHeader: (params: GridColumnHeaderParams) => columnRenderHeader(params.field), cellClassName: getCellClassName },
  { field: 'Gaps', width: 120, sortable: false, filterable: false, disableColumnMenu: true, renderHeader: (params: GridColumnHeaderParams) => columnRenderHeader(params.field), cellClassName: getCellClassName },
  { field: 'Duplicated Geometries', width: 150, sortable: false, filterable: false, disableColumnMenu: true, cellClassName: getCellClassName },
  { field: 'Feature within other features', width: 150, sortable: false, filterable: false, disableColumnMenu: true, cellClassName: getCellClassName },
  { field: 'Not Within Parent', width: 170, sortable: false, filterable: false, disableColumnMenu: true, renderHeader: (params: GridColumnHeaderParams) => columnRenderHeader(params.field), cellClassName: getCellClassName },
  { field: 'Parent Code Missing', sortable: false, filterable: false, disableColumnMenu: true, cellClassName: getCellClassName },
  { field: 'Default Code Missing', sortable: false, filterable: false, disableColumnMenu: true, cellClassName: getCellClassName },
  { field: 'Default Name Missing', sortable: false, filterable: false, disableColumnMenu: true, cellClassName: getCellClassName },
  { field: 'Privacy Level Missing', sortable: false, filterable: false, disableColumnMenu: true, cellClassName: getCellClassName },
  { field: 'Parent Missing', width: 160, sortable: false, filterable: false, disableColumnMenu: true, renderHeader: (params: GridColumnHeaderParams) => columnRenderHeader(params.field), cellClassName: getCellClassName },
  { field: 'Duplicated Codes', width: 170, sortable: false, filterable: false, disableColumnMenu: true, renderHeader: (params: GridColumnHeaderParams) => columnRenderHeader(params.field), cellClassName: getCellClassName },
  { field: 'Invalid Privacy Level', width: 180, sortable: false, filterable: false, disableColumnMenu: true , renderHeader: (params: GridColumnHeaderParams) => columnRenderHeader(params.field), cellClassName: getCellClassName},
  { field: 'Upgraded Privacy Level', width: 200, sortable: false, filterable: false, disableColumnMenu: true, renderHeader: (params: GridColumnHeaderParams) => columnRenderHeader(params.field), cellClassName: getCellClassName },
]

const columnGroupingModel: GridColumnGroupingModel = [
  {
    groupId: 'Geometry Validity Checks',
    description: '',
    children: [
      { field: 'Self Intersects' },
      // { field: 'Self Contacts' },
      { field: 'Duplicate Nodes' },
      { field: 'Polygon with less than 4 nodes' },
    ],
  },
  {
    groupId: 'Geometry Topology Checks',
    description: '',
    children: [
      { field: 'Overlaps' },
      { field: 'Gaps' },
      { field: 'Duplicated Geometries' },
      { field: 'Feature within other features' },
      { field: 'Not Within Parent' },
    ],
  },
  {
    groupId: 'Attributes Checks',
    description: '',
    children: [
      { field: 'Parent Code Missing' },
      { field: 'Default Code Missing' },
      { field: 'Default Name Missing' },
      { field: 'Privacy Level Missing' },
      { field: 'Parent Missing' },
      { field: 'Duplicated Codes' },
      { field: 'Invalid Privacy Level' },
      { field: 'Upgraded Privacy Level' },
    ],
  },
]

const COLUMN_DESCRIPTION: {
  [key: string]: string,
 } = {
  'Self Intersects': 'Check for self-intersects using GEOSisValidDetail with flag 1',
  'Duplicate Nodes': 'Check for duplicate nodes',
  'Polygon with less than 4 nodes': 'Check if polygon with less than 4 nodes',
  'Overlaps': 'Check for overlapping polygons smaller than (map units sqr.)',
  'Gaps': 'Checks for gaps between neighbouring polygons smaller than (map units sqr.)',
  'Duplicated Geometries': 'There are entities in the same level with same geometries',
  'Feature within other features': 'Check whether feature is within other features',
  'Not Within Parent': 'Child geometry is not within parent geometry',
  'Parent Code Missing': 'Empty/Missing Parent Id Field',
  'Default Code Missing': 'Empty/Missing Default Code/Id Field',
  'Default Name Missing': 'Empty/Missing Default Name',
  'Privacy Level Missing': 'Empty/Missing Privacy Level',
  'Parent Missing': 'Cannot find parent from upper level by its Parent Id Field',
  'Duplicated Codes': 'There is default code that is not unique',
  'Invalid Privacy Level': 'Privacy level is higher than maximum level in dataset configuration',
  'Upgraded Privacy Level': 'Privacy level has been upgraded to dataset minimum privacy level',
}


const IN_PROGRES_STATUS_LIST = ['Started', 'Processing']


export default function Step4(props: WizardStepInterface) {
  const [uploadData, setUploadData] = useState<any[]>([])
  const [errorSummaries, setErrorSummaries] = useState<any[]>([])
  const [errorReportPath, setErrorReportPath] = useState<string>('')
  const [hasErrorOverlaps, setHasErrorOverlaps] = useState(false)
  const [viewOverlapId, setViewOverlapId] = useState<number>(null)
  const [allFinished, setAllFinished] = useState<boolean>(false)
  const [openErrorModal, setOpenErrorModal] = useState<boolean>(false)
  const [selectedEntities, setSelectedEntities] = useState<number[]>([])
  const url = URL + `?id=${props.uploadSession}`
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const dispatch = useAppDispatch()
  const [viewOverlapError, setViewOverlapError] = useState(false)
  const [customColumnOptions, setCustomColumnOptions] = useState({
    'status': {
        filter: true,
        sort: true,
        display: true,
        customBodyRender: (value: any, tableMeta: any, updateValue: any) => {
          let id = tableMeta['rowData'][0]
          let isImportable = tableMeta['rowData'][6]
          let isWarning = tableMeta['rowData'][7]
          let progress = tableMeta['rowData'][8] ? tableMeta['rowData'][8] : ''
          let summaries = tableMeta['rowData'][4]
          let error_report = tableMeta['rowData'][5]
          if (IN_PROGRES_STATUS_LIST.includes(value)) {
            return <span style={{display:'flex'}}>
                    <CircularProgress size={18} />
                    <span style={{marginLeft: '5px' }}>{value}{value === 'Processing' && progress ? ` ${progress}`:''}</span>
                  </span>
          } else  if (value === 'Error') {
            if (props.isReadOnly) {
              return <span>
                      <span>{isWarning?'Warning':value}</span>
                      <Button id={`error-btn-${id}`} variant={'contained'} color={isWarning?"warning":"error"} onClick={
                        () => showError(id, summaries, error_report, isImportable)} style={{marginLeft:'10px'}}
                      >{isWarning?'Show Warning':'Show Error'}</Button>
                    </span>
            } else {
              return <Button id={`error-btn-${id}`} variant={'contained'} color={isWarning?"warning":"error"} onClick={
                        () => showError(id, summaries, error_report, isImportable)}
                      >{isWarning?'Show Warning':'Show Error'}</Button>
            }
          }
          return value
        }
    }
  })

  const getStatus = () => {
    axios.get(url).then(
      response => {
        if (response.data && response.data['is_read_only']){
          let _results = response.data['results']
          setAllFinished(true)
          setUploadData(_results.map((responseData: any) => {
            const uploadRow: any = {}
            for (let key of Object.keys(responseData)) {
                uploadRow[key] = responseData[key]
            }
            uploadRow['started at'] = utcToLocalDateTimeString(new Date(uploadRow['started at']))
            return uploadRow
          }))
        } else if (response.data && response.data['results']) {
          let _results = response.data['results']
          const unfinished = _results.filter((responseData: any) => {
            return responseData['status'] == 'Started' || responseData['status'] == 'Processing';
          })
          if (unfinished.length == 0) {
            setAllFinished(true)
            const errors = _results.filter((responseData: any) => {
              return responseData['status'] == 'Error';
            })
            props.setEditable(true)
            if (props.onCheckProgress) {
              props.onCheckProgress()
            }
          } else {
            props.setEditable(false)
          }
          setUploadData(_results.map((responseData: any) => {
            const uploadRow: any = {}
            for (let key of Object.keys(responseData)) {
                uploadRow[key] = responseData[key]
            }
            uploadRow['started at'] = utcToLocalDateTimeString(new Date(uploadRow['started at']))
            return uploadRow
          }))
        }
      }
    )
  }

  useEffect(() => {
    if (uploadData.length > 0 && !allFinished) {
      const interval = setInterval(() => {
        getStatus()
      }, 5000);
      return () => clearInterval(interval);
    }
  }, [uploadData, allFinished])

  useEffect(() => {
    getStatus()
  }, [searchParams])

  const showError = async (id: any, errorSummariesData: any[], errorPath: string, is_importable: boolean) => {
    setErrorSummaries(errorSummariesData)
    setErrorReportPath(errorPath)
    let _hasErrorOverlaps = false
    let _view_overlaps = null
    for (let summary of errorSummariesData) {
      if (summary['Overlaps'] > 0) {
        _hasErrorOverlaps = true
        _view_overlaps = id
        break
      }
    }
    // show overlaps error when there is only overlaps error and no other error
    // because current logic will remove the entities
    setHasErrorOverlaps(_hasErrorOverlaps && is_importable)
    setViewOverlapId(_view_overlaps)
    setOpenErrorModal(true)
  }

  const selectionChanged = (data: any) => {
    setSelectedEntities(data)
  }

  const downloadReport = (reportPath: string) => {
    const link = document.createElement("a");
    link.download = `error_report.csv`;
    link.href = reportPath;
    link.click();
  }

  const handleImportClick = () => {
    postData(
      READY_TO_REVIEW_URL,
      {
        'upload_entities': selectedEntities.join(',')
      }
    ).then((response) => {
      if (response.status === 200) {
        // trigger to fetch notification frequently
        dispatch(setPollInterval(FETCH_INTERVAL_JOB))
        if ((window as any).is_admin && 'session_id' in response.data) {
          let _id = response.data['session_id']
          navigate(`${ReviewListRoute.path}?upload=${_id}`)
        } else {
          navigate(ReviewListRoute.path)
        }
      }
    }).catch((error) => {
      if (error.response && error.response.data && error.response.data['detail']) {
        alert(error.response.data['detail'])
      } else {
        alert("Error importing data")
      }
    })
  }

  const canRowBeSelected = (dataIndex: number, rowData: any) => {
    if (props.isReadOnly || !allFinished)
      return false
    return rowData['is_importable']
  }

  const getColumnHeader = (header: string) => {
    if (!(header in COLUMN_DESCRIPTION)) {
      return header
    }

    return <ColumnHeaderIcon title={header} tooltipTitle={header}
      tooltipDescription={<p>{COLUMN_DESCRIPTION[header]}</p>}
    />
  }

  return (
    <Scrollable>
    <div className="Step3Container Step4Container">
      <Modal open={openErrorModal} onClose={() => {
            setOpenErrorModal(false)
            setViewOverlapError(false)
          }}
      >
        <Box className="error-modal" sx={{minHeight: '60%'}}>
          { viewOverlapError && <Step4OverlapsError upload_id={viewOverlapId} onBackClicked={() => setViewOverlapError(false)} /> }
          { !viewOverlapError && (
            <Grid container flexDirection={'column'} sx={{height: '100%', flex: 1}}>
              <h2>Error</h2>
              <Box  sx={{width: '100%', overflowX: 'auto', height: '450px'}}>
                <DataGrid
                  getRowId={(row) => row['Level']}
                  experimentalFeatures={{ columnGrouping: true }}
                  rows={errorSummaries}
                  columns={columns}
                  columnGroupingModel={columnGroupingModel}
                  sx={{
                    '& .MuiDataGrid-columnHeaderTitle': {
                      whiteSpace: 'normal',
                      lineHeight: 'normal',
                      fontWeight: '500 !important'
                    },
                    '& .MuiDataGrid-columnHeader': {
                      // Forced to use important since overriding inline styles
                      height: 'unset !important',
                      color: 'unset !important'
                    },
                    '& .MuiDataGrid-columnHeaders': {
                      // Forced to use important since overriding inline styles
                      maxHeight: '168px !important'
                    },
                  }}
                />
              </Box>
              <Box  sx={{width: '100%'}}>
              { errorReportPath ? (
                <Box className={'error-report-button-container'}>
                  <Grid container flexDirection={'row'} justifyContent={'space-between'}>
                    <Grid item>
                      {/* { hasErrorOverlaps && <Button variant={'outlined'} onClick={() => setViewOverlapError(true)}>
                        View Overlaps Error
                      </Button>} */}
                    </Grid>
                    <Grid item>
                      <Button variant={'contained'} onClick={() => downloadReport(errorReportPath)}>
                        Download Error Report
                      </Button>
                    </Grid>
                  </Grid>
                  
                </Box>
              ) : null}
              </Box>
            </Grid>
          )}
        </Box>
      </Modal>
      <List
        pageName={'Country'}
        listUrl={''}
        initData={uploadData}
        isRowSelectable={allFinished}
        selectionChanged={selectionChanged}
        canRowBeSelected={canRowBeSelected}
        editUrl={''}
        excludedColumns={['is_importable', 'progress', 'error_summaries', 'error_report', 'is_warning']}
        customOptions={customColumnOptions}
      />
        <div className="button-container" style={{marginLeft:0, width: '100%'}}>
          <Grid container direction='row' justifyContent='space-between'>
            <Grid item>
              <Button disabled={!allFinished} onClick={() => props.onBackClicked()} variant="outlined">
                Back
              </Button>
            </Grid>
            <Grid item>
              { !props.isReadOnly && (
                <Button variant="contained"
                    disabled={selectedEntities.length == 0}
                    onClick={handleImportClick}
                >Import</Button>
              )}
            </Grid>
          </Grid>

        </div>
    </div>
    </Scrollable>
  )
}
