import React, {useLayoutEffect, useEffect, useState, useRef, useCallback} from 'react';
import MUIDataTable, {debounceSearchRender, MUISortOptions} from "mui-datatables";
import {
    Grid,
    Button,
    FormGroup,
    TextField,
    FormLabel,
} from "@mui/material";
import axios from "axios";
import {EntitiesFilterInterface, EntitiesFilterUpdateInterface} from "./EntitiesFilter"
import FilterAlt from '@mui/icons-material/FilterAlt';
import {LocalizationProvider} from "@mui/x-date-pickers";
import {AdapterDateFns} from "@mui/x-date-pickers/AdapterDateFns";
import { DateTimePicker } from '@mui/x-date-pickers';
import {TABLE_OFFSET_HEIGHT} from "../../components/List"
import ResizeTableEvent from "../../components/ResizeTableEvent"
import Loading from "../../components/Loading";
import PaginationInterface, { getDefaultPagination, rowsPerPageOptions } from '../../models/pagination';

export interface EntitiesTableInterface {
    dataset_id: string,
    session: string,
    filter: EntitiesFilterInterface,
    onLoadStarted?: () => void,
    onLoadCompleted?: (success: boolean) => void,
    onEntitySelected?: (id: number) => void,
    onFilterUpdated?: (new_filters: EntitiesFilterUpdateInterface[]) => void,
    onSingleFilterUpdated? : (data: EntitiesFilterUpdateInterface) => void,
    onRowHover?: (id: number, level: number, centroid?: any) => void,
    viewUuid?: string
}

const COLUMNS = [
    'id',
    'country',
    'level',
    'type',
    'name',
    'default_code',
    'code',
    'concept_ucode',
    'updated',
    'rev',
    'status',
    'centroid'
]


interface EntityTableRowInterface {
    id: number,
    country: string,
    level: number,
    type: string,
    name: string,
    default_code: string,
    code: string,
    concept_ucode: string,
    updated: Date,
    rev: number,
    status: string,
    centroid: any
}

const FILTER_VALUES_API_URL = '/api/dashboard-dataset-filter/values/'
const API_URL = '/api/dashboard-dataset/list/'

const FilterIcon: any = FilterAlt

export default function EntitiesTable(props: EntitiesTableInterface) {
    const [loading, setLoading] = useState<boolean>(true)
    const [columns, setColumns] = useState<any>([])
    const [data, setData] = useState<EntityTableRowInterface[]>([])
    const [totalCount, setTotalCount] = useState<number>(0)
    const [pagination, setPagination] = useState<PaginationInterface>(getDefaultPagination())
    const [filterValues, setFilterValues] = useState({})
    const ref = useRef(null)
    const [tableHeight, setTableHeight] = useState(0)
    const axiosSource = useRef(null)
    const newCancelToken = useCallback(() => {
        axiosSource.current = axios.CancelToken.source();
        return axiosSource.current.token;
      }, [])

    const fetchFilterValues = async () => {
        if (Object.keys(filterValues).length != 0) return filterValues
        let _query_params = ''
        if (props.viewUuid) {
            _query_params = _query_params + (_query_params?'&':'') + `view_uuid=${props.viewUuid}`
        }
        let filters = []
        filters.push(axios.get(`${FILTER_VALUES_API_URL}${props.dataset_id}/country/?${_query_params}`))
        filters.push(axios.get(`${FILTER_VALUES_API_URL}${props.dataset_id}/level/?${_query_params}`))
        filters.push(axios.get(`${FILTER_VALUES_API_URL}${props.dataset_id}/level_name/?${_query_params}`))
        filters.push(axios.get(`${FILTER_VALUES_API_URL}${props.dataset_id}/type/?${_query_params}`))
        filters.push(axios.get(`${FILTER_VALUES_API_URL}${props.dataset_id}/revision/?${_query_params}`))
        filters.push(axios.get(`${FILTER_VALUES_API_URL}${props.dataset_id}/status/?${_query_params}`))
        let resultData = await Promise.all(filters)
        let filter_values = {
            'country': resultData[0].data,
            'level': resultData[1].data,
            'name': resultData[2].data,
            'type': resultData[3].data,
            'rev': resultData[4].data,
            'status': resultData[5].data,
        }
        setFilterValues(filter_values)
        return filter_values
    }

    const fetchEntities = (cancelFetchToken:any) => {
        setData([])
        setLoading(true)
        if (props.onLoadStarted) {
            props.onLoadStarted()
        }
        let sort_by = pagination.sortOrder.name ? pagination.sortOrder.name : ''
        let sort_direction = pagination.sortOrder.direction ? pagination.sortOrder.direction : ''
        let _query_params = `page=${pagination.page+1}&page_size=${pagination.rowsPerPage}&sort_by=${sort_by}&sort_direction=${sort_direction}`
        if (props.viewUuid) {
            _query_params = _query_params + `&view_uuid=${props.viewUuid}`
        }
        // API call using props.filter
        axios.post(`${API_URL}${props.dataset_id}/${props.session}/?${_query_params}`,
            props.filter, {
            cancelToken: cancelFetchToken
        }).then(
            response => {
                setData(response.data.results as EntityTableRowInterface[])
                setTotalCount(response.data.count)
                if (props.onLoadCompleted) {
                    props.onLoadCompleted(true)
                }
                setLoading(false)
            }
          ).catch(error => {
            if (!axios.isCancel(error)) {
                console.log(error)
                setLoading(false)
            }                
            if (props.onLoadCompleted) {
                props.onLoadCompleted(false)
            }
          })
    }

    const triggerFetchEntitiesAPI = () => {
        if (axiosSource.current) axiosSource.current.cancel()
        let cancelFetchToken = newCancelToken()
        fetchEntities(cancelFetchToken)
    }

    useEffect(() => {
        const fetchFilterValuesData = async() => {
            let filter_values:any = await fetchFilterValues()
            if (columns.length === 0) {
                setColumns(COLUMNS.map((column_name) => {
                    let options:any = {
                        name: column_name,
                        data_type: (column_name !== 'id' && column_name !== 'centroid') ?'string_array':'',
                        label: column_name.charAt(0).toUpperCase() + column_name.slice(1).replaceAll('_', ' '),
                        options: {
                        }
                    }
                    if (column_name === 'updated') {
                        options.data_type = 'date_range'
                        options.label = 'Valid From'
                        options.options = {
                            searchable: false,
                            display: true,
                            customBodyRender: (value:any) => {
                                return value?new Date(value).toLocaleString([], {dateStyle: 'short', timeStyle: 'short'}):'-'
                            },
                            filter: true,
                            filterType: 'custom',
                            filterOptions: {
                                logic(val:any, filters:any) {
                                    return false;
                                },
                                display: (filterList: any, onChange: any, index: any, column: any) => (
                                    <div>
                                    <FormLabel>Valid On</FormLabel>
                                    <FormGroup row>
                                        <LocalizationProvider dateAdapter={AdapterDateFns}>
                                            <DateTimePicker
                                                label=""
                                                inputFormat="MM/dd/yyyy hh:mm a"
                                                value={filterList[index][0] || null}
                                                PopperProps={{
                                                    placement: "top-end",
                                                }}
                                                renderInput={(params: any) => <TextField required={false} {...params} sx={{ marginRight: 2 }}/>}
                                                onChange={(val) => {
                                                    filterList[index][0] = val
                                                    onChange(filterList[index], index, column)
                                            }}/>
                                        </LocalizationProvider>
                                    </FormGroup>
                                    </div>
                                )
                            },
                            customFilterListOptions: {
                                render: (v:any):any => {
                                    return v && v.length && v[0]?'Valid On '+new Date(v[0]).toLocaleString([], {dateStyle: 'short', timeStyle: 'short'}):[]
                                },
                                update: (filterList:any, filterPos:any, index:any) => {
                                    if (filterPos === -1) {
                                        filterList[index] = []
                                        handleDateOnClear()
                                    }
                                    return filterList;
                                }
                            }                        
                        }
                    } else {
                        options.options = {
                            searchable: false,
                            display: column_name !== 'id' && column_name !== 'centroid',
                            filter: column_name !== 'id' && column_name !== 'code' && column_name !== 'default_code' && column_name !== 'concept_ucode',
                        }
                        if (column_name === 'level') {
                            options.options.customFilterListOptions = {
                                render: (v:any) => `Level ${v}`
                            }
                        } else if (column_name === 'rev') {
                            options.options.customFilterListOptions = {
                                render: (v:any) => `Revision ${v}`
                            }
                        } else if (column_name === 'centroid') {
                            // this is for filtering by points
                            options.options.customFilterListOptions = {
                                render: (points:any) => {
                                    let result:string[] = []
                                    for (let point of points)
                                        result.push(`Point ${point.length == 3 ? point[2]: '-'}`)
                                    return result
                                },
                                update: (filterList:any, filterPos:any, index:any) => {
                                    filterList[index].splice(filterPos, 1)
                                    handleFilterPointOnChange(filterList[index])
                                    return filterList;
                                }
                            }
                            options.options.filterType = 'custom'
                            options.options.filterOptions = {
                                logic: (location:any, filters:any, row:any) => {
                                    return false
                                },
                                display: (filterList:any, onChange:any, index:any, column:any):any => {
                                    return null
                                }
                            }

                        }
                        if (filter_values[column_name] !== undefined) {
                            // set filter values in dropdown
                            options.options.filterOptions = {
                                names: filter_values[column_name]
                            }
                        }
                        if (column_name === 'country' || column_name === 'level' || column_name === 'type' ||
                            column_name === 'name' || column_name === 'status' || column_name === 'rev' || column_name === 'centroid') {
                            // set existing filter values 
                            options.options.filterList = getExistingFilterValue(column_name)
                        }
                    }
                    return options
                }))
            } else {
                // update existing filters from props Filter obj
                const _columns = columns.map((column: any) => {
                    if (column.name === 'country' || column.name === 'level' || column.name === 'type' ||
                            column.name === 'name' || column.name === 'status' || column.name === 'rev' || column.name === 'centroid') {
                        let _opt = {...column.options}
                        _opt.filterList = getExistingFilterValue(column.name)
                        return { ...column, options: _opt}
                    } else if (column.name === 'updated') {
                        let _opt = {...column.options}
                        _opt.filterList = []
                        if (props.filter.valid_from !== null)
                            _opt.filterList = [props.filter.valid_from]
                        return { ...column, options: _opt}
                    }

                    return column
                })
                setColumns(_columns)
            }
            if (props.filter.updated_at != null && props.session) {
                triggerFetchEntitiesAPI()
            }
        }
        fetchFilterValuesData()
    }, [props.filter.updated_at])

    useEffect(() => {
        if (props.session)
            triggerFetchEntitiesAPI()
    }, [pagination])

    const handleFilterSubmit = (applyFilters: any) => {
        let filterList = applyFilters()
        let filters:EntitiesFilterUpdateInterface[] = []
        for (let idx in filterList) {
            let col = columns[idx]
            if (!col.options.filter)
                continue
            let filter:EntitiesFilterUpdateInterface = {
                criteria: col.name,
                type: col.data_type,
                values: [],
                date_from: null,
                date_to: null
            }
            filter.criteria = getCriteriaFromColumnName(filter.criteria)
            if (filterList[idx] && filterList[idx].length) {
                if (col.data_type === 'string_array') {
                    filter.values = filterList[idx]
                } else if (col.data_type === 'date_range') {
                    filter.date_from = filterList[idx][0]
                }
            }
            filters.push(filter)
        }
        if (props.onFilterUpdated)
            props.onFilterUpdated(filters)
    }

    const handleSearchOnChange = (search_text: string) => {
        if (!props.onSingleFilterUpdated) return;
        props.onSingleFilterUpdated({
            criteria: 'search_text',
            type: 'string_search',
            values: [search_text?search_text:''],
            date_from: null,
            date_to: null
        })
    }

    const handleDateOnClear = () => {
        if (!props.onSingleFilterUpdated) return;
        props.onSingleFilterUpdated({
            criteria: 'valid_on',
            type: 'date_range',
            values: [],
            date_from: null,
            date_to: null
        })
    }

    const handleFilterPointOnChange = (pointFilter: any) => {
        if (!props.onSingleFilterUpdated) return;
        props.onSingleFilterUpdated({
            criteria: 'points',
            type: 'string_array',
            values: pointFilter,
            date_from: null,
            date_to: null
        })
    }

    const getCriteriaFromColumnName = (col_name: string): string => {
        let val = col_name;
        if (col_name === 'name')
            val = 'level_name'
        else if (col_name === 'rev')
            val = 'revision'
        else if (col_name === 'updated')
            val = 'valid_on'
        return val;
    }

    const getExistingFilterValue = (col_name: string):string[] =>  {
        let values:string[] = []
        switch (col_name) {
            case 'country':
                values = props.filter.country
                break;
            case 'level':
                values = props.filter.level
                break;
            case 'type':
                values = props.filter.type
                break;
            case 'name':
                values = props.filter.level_name
                break;
            case 'rev':
                values = props.filter.revision
                break;
            case 'status':
                values = props.filter.status
                break;
            case 'centroid':
                values = props.filter.points
                break;
            default:
                break;
        }
        return values
    }
    
    const onRowMouseEnter =  (row: any) => {
        if (row && row.length > 0) {
            if (props.onRowHover) {
                props.onRowHover(row[0], row[2], [])
            }
                
        }
    }

    const onRowMouseLeave =  () => {
        if (props.onRowHover)
            props.onRowHover(0, 0, [])
    }

    const onTableChangeState = (action:string, tableState:any) => {
        switch (action) {
            case 'changePage':
                setPagination({
                    ...pagination,
                    page: tableState.page
                })
                break;
            case 'sort':
                setPagination({
                    ...pagination,
                    page: 0,
                    sortOrder: tableState.sortOrder
                })
                break;
            case 'changeRowsPerPage':
                setPagination({
                    ...pagination,
                    page: 0,
                    rowsPerPage: tableState.rowsPerPage
                })
                break;
            default:
          }
    }

    return (
        <Grid className={'entities-table-root'} container ref={ref}>
            <Grid item className={'entities-table'}>
                <MUIDataTable columns={columns} data={data}
                        title=''
                        options={{
                            selectableRows: 'none',
                            onRowClick: (rowData: string[]) => {
                                if (!props.onEntitySelected) return;
                                props.onEntitySelected(parseInt(rowData[0]))
                            },
                            serverSide: true,
                            page: pagination.page,
                            count: totalCount,
                            rowsPerPage: pagination.rowsPerPage,
                            rowsPerPageOptions: rowsPerPageOptions,
                            sortOrder: pagination.sortOrder as MUISortOptions,
                            jumpToPage: true,
                            onTableChange: (action:string, tableState:any) => onTableChangeState(action, tableState),
                            fixedHeader: true,
                            tableBodyMaxHeight: `${tableHeight}px`,
                            tableBodyHeight: `${tableHeight}px`,
                            download: false,
                            print: false,
                            viewColumns: false,
                            confirmFilters: true,
                            filter: true,
                            filterType: 'multiselect',
                            rowHover: true,
                            customSearchRender: debounceSearchRender(500),
                            customFilterDialogFooter: (currentFilterList, applyNewFilters) => {
                                return (
                                  <div style={{ marginTop: '40px' }}>
                                    <Button variant="contained" onClick={() => handleFilterSubmit(applyNewFilters)}>Apply Filters</Button>
                                  </div>
                                );
                            },
                            onFilterChange: (column, filterList, type) => {
                                if (type === 'chip') {
                                  var newFilters = () => (filterList)
                                  handleFilterSubmit(newFilters)
                                }
                            },
                            onSearchChange: (searchText: string) => {
                                handleSearchOnChange(searchText)
                            },
                            searchText: props.filter.search_text,
                            searchOpen: (props.filter.search_text != null && props.filter.search_text.length > 0),
                            setRowProps:(row, dataIndex, rowIndex) => {
                                return {
                                  onMouseEnter: (e:any) => onRowMouseEnter(row),
                                  onMouseLeave: (e:any) => onRowMouseLeave()
                                }
                            },
                            textLabels: {
                                body: {
                                    noMatch: loading ?
                                        <Loading /> :
                                        'Sorry, there is no matching data to display',
                                },
                            },
                        }}
                        components={{
                            icons: {
                              FilterIcon
                            }
                          }}
                        />
                
                <ResizeTableEvent containerRef={ref} onBeforeResize={() => setTableHeight(0)}
                    onResize={(clientHeight:number) => {
                        setTableHeight(clientHeight - TABLE_OFFSET_HEIGHT)
                    }} />
            </Grid>
        </Grid>
    )

}
